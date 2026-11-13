"""A request that broke a rule: WHAT broke, WHY the rule exists, HOW to fix it."""

from __future__ import annotations

from nwstep.domain.fault import Fault


class Refusal(Exception):
    """Raised before anything is written. The HOW line is filled in by the application layer."""

    def __init__(
        self,
        what: str,
        why: str,
        how: str | None = None,
        *,
        field: str | None = None,
        rejected: tuple[str, ...] = (),
        missing: tuple[str, ...] = (),
        fault: Fault | None = None,
    ) -> None:
        super().__init__(what)
        self.what = what
        self.why = why
        self.how = how
        self.field = field
        self.rejected = rejected
        self.missing = missing
        self.fault = fault

    def with_how(self, how: str) -> Refusal:
        return Refusal(
            self.what,
            self.why,
            how,
            field=self.field,
            rejected=self.rejected,
            missing=self.missing,
            fault=self.fault,
        )

    def with_what(self, what: str) -> Refusal:
        """The same refusal with its WHAT replaced: used when a refusal of a replayed step must name the context it came from."""
        return Refusal(
            what,
            self.why,
            self.how,
            field=self.field,
            rejected=self.rejected,
            missing=self.missing,
            fault=self.fault,
        )
