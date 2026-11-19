"""The one real HTTP transport: the standard library, the run's token, a timeout of 30 seconds."""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import TYPE_CHECKING

from scripts.public_issues.api_error import ApiError
from scripts.public_issues.http_response import HttpResponse


if TYPE_CHECKING:
    from collections.abc import Mapping


def send(
    method: str, url: str, headers: Mapping[str, str], body: bytes | None
) -> HttpResponse:
    request = urllib.request.Request(
        url, data=body, method=method, headers=dict(headers)
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return HttpResponse(
                response.status, dict(response.headers.items()), response.read()
            )
    except urllib.error.HTTPError as error:
        return HttpResponse(error.code, dict(error.headers.items()), error.read())
    except (urllib.error.URLError, OSError) as error:
        raise ApiError(
            f"the request to {method} {url.split('?', maxsplit=1)[0]} did not complete",
            f"the network or the service did not answer: {error}",
            "check the network and run the job again; nothing was written on this call",
        ) from error
