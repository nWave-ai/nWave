"""The GitHub REST calls the sweep makes, over one injected transport. Every refusal raises ApiError."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from scripts.public_issues.api_error import ApiError
from scripts.public_issues.http_response import HttpResponse


API = "https://api.github.com"
Transport = Callable[[str, str, Mapping[str, str], bytes | None], HttpResponse]


class GitHubApi:
    def __init__(self, repository: str, token: str, transport: Transport) -> None:
        self._base = f"{API}/repos/{repository}"
        self._transport = transport
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "nwave-public-issues",
        }

    def issues_with_label(self, state: str, label: str) -> list[dict[str, Any]]:
        listed = self._pages(
            f"/issues?state={state}&labels={quote(label)}&per_page=100"
        )
        return [item for item in listed if "pull_request" not in item]

    def issue_json(self, number: int) -> dict[str, Any]:
        response = self._send("GET", f"{self._base}/issues/{number}")
        return self._object(response, f"issue {number}")

    def comments_json(self, number: int) -> list[dict[str, Any]]:
        return self._pages(f"/issues/{number}/comments")

    def label_names(self) -> frozenset[str]:
        return frozenset(item["name"] for item in self._pages("/labels"))

    def create_label(self, name: str) -> None:
        self._send(
            "POST",
            f"{self._base}/labels",
            {"name": name, "color": "ededed"},
            expect=201,
        )

    def add_label(self, number: int, name: str) -> None:
        self._send("POST", f"{self._base}/issues/{number}/labels", {"labels": [name]})

    def remove_label(self, number: int, name: str) -> None:
        self._send("DELETE", f"{self._base}/issues/{number}/labels/{quote(name)}")

    def set_state(self, number: int, state: str, reason: str | None = None) -> None:
        body: dict[str, str] = {"state": state}
        if reason is not None:
            body["state_reason"] = reason
        self._send("PATCH", f"{self._base}/issues/{number}", body)

    def post_comment(self, number: int, text: str) -> None:
        self._send(
            "POST", f"{self._base}/issues/{number}/comments", {"body": text}, expect=201
        )

    def _pages(self, path: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        url: str | None = self._base + path
        while url is not None:
            response = self._send("GET", url)
            items.extend(self._array(response, url))
            url = _next_page(response.header("link"))
        return items

    def _send(
        self,
        method: str,
        url: str,
        payload: dict[str, Any] | None = None,
        expect: int | None = None,
    ) -> HttpResponse:
        headers = dict(self._headers)
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        response = self._transport(method, url, headers, body)
        accepted = (expect,) if expect is not None else tuple(range(200, 300))
        if response.status not in accepted:
            raise _refusal(method, url, response)
        return response

    def _object(self, response: HttpResponse, what: str) -> dict[str, Any]:
        value = _decode(response)
        if not isinstance(value, dict):
            raise _not_json(what)
        return value

    def _array(self, response: HttpResponse, url: str) -> list[dict[str, Any]]:
        value = _decode(response)
        if not isinstance(value, list):
            raise _not_json(url.split("?", maxsplit=1)[0])
        return value


def _decode(response: HttpResponse) -> object:
    try:
        return json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise ApiError(
            "GitHub answered with a body that is not JSON",
            f"the body could not be parsed: {error}",
            "run the job again; no decision was applied on this read",
        ) from error


def _not_json(what: str) -> ApiError:
    return ApiError(
        f"GitHub answered with an unexpected shape for {what}",
        "the body is not the list or object the rule reads",
        "run the job again; no decision was applied on this read",
    )


def _refusal(method: str, url: str, response: HttpResponse) -> ApiError:
    path = url.split("?", maxsplit=1)[0].replace(API, "")
    if response.status in (403, 429) and _rate_limited(response):
        reset = response.header("x-ratelimit-reset")
        when = (
            f"the limit resets at {datetime.fromtimestamp(int(reset), UTC).strftime('%H:%M:%S UTC')}"
            if reset and reset.isdigit()
            else "the limit resets later"
        )
        return ApiError(
            f"GitHub refused {method} {path} because the rate limit is reached",
            f"no more calls are allowed until the limit resets; {when}",
            "wait for the reset and run the job again; no decision was applied on this read",
        )
    message = _message(response)
    return ApiError(
        f"GitHub answered {response.status} for {method} {path}",
        f"the request was refused{': ' + message if message else ''}",
        "check that the token has issues write and contents read and that the repository "
        "name is right, then run the job again",
    )


def _rate_limited(response: HttpResponse) -> bool:
    return (
        response.header("x-ratelimit-remaining") == "0"
        or response.header("retry-after") is not None
    )


def _message(response: HttpResponse) -> str:
    try:
        value = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return ""
    return str(value.get("message", "")) if isinstance(value, dict) else ""


def _next_page(link: str | None) -> str | None:
    if not link:
        return None
    for part in link.split(","):
        pieces = part.split(";")
        if len(pieces) == 2 and pieces[1].strip() == 'rel="next"':
            return pieces[0].strip().strip("<>")
    return None
