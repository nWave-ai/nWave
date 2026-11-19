"""Who wrote a comment or opened an issue, as far as the silence rule needs to know."""

from __future__ import annotations

from dataclasses import dataclass


MAINTAINER_ASSOCIATIONS = frozenset({"OWNER", "MEMBER", "COLLABORATOR"})


@dataclass(frozen=True)
class Author:
    login: str
    association: str
    account_type: str

    @property
    def is_bot(self) -> bool:
        return self.account_type == "Bot" or self.login.endswith("[bot]")

    @property
    def is_maintainer(self) -> bool:
        return self.association in MAINTAINER_ASSOCIATIONS
