"""The time bound of a command field: the seconds its command may run, the default and the ceiling.

The bound limits the command's own running time. The wait for a place in the shared test queue is not counted in it:
the queue's clock starts when the command gets its place (measured on the queue of this account).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nwstep.domain.fault import Fault
from nwstep.domain.refusal import Refusal


if TYPE_CHECKING:
    from nwstep.domain.field import Field


class CommandBound:
    DEFAULT_SECONDS = 300
    CEILING_SECONDS = 3600

    @classmethod
    def resolve(cls, field: Field, values: dict[str, Any]) -> int:
        """The bound of a command field: the seconds its declared bound field holds, else the default."""
        if field.bound is None or values.get(field.bound) is None:
            return cls.DEFAULT_SECONDS
        return cls.declared(values[field.bound], field.bound)

    @classmethod
    def declared(cls, seconds: object, field_name: str) -> int:
        """The declared seconds, when they are a whole number from 1 up to the ceiling; otherwise a refusal."""
        if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds < 1:
            raise Refusal(
                what=f"'{field_name}' must be a whole number of seconds of at least 1, got {seconds!r}",
                why="the bound is the time the command may run; a bound that is not a positive whole number of seconds cannot be enforced",
                how=f"declare the seconds as a whole number, for example --{field_name} {cls.DEFAULT_SECONDS}",
                field=field_name,
                fault=Fault.VALUE,
            )
        if seconds > cls.CEILING_SECONDS:
            raise Refusal(
                what=f"'{field_name}' is {seconds} seconds, above the ceiling of {cls.CEILING_SECONDS} seconds",
                why="a command may hold its place in the shared test queue for at most the ceiling, so one record cannot hold the box for longer",
                how=f"declare at most {cls.CEILING_SECONDS} seconds, or make the command faster",
                field=field_name,
                fault=Fault.VALUE,
            )
        return seconds
