"""Every interface crossed with every category needs one cell: a case with its expected result, or a reasoned n/a."""

from __future__ import annotations

from nwstep.domain.fault import Fault
from nwstep.domain.field import Field
from nwstep.domain.matrix_cell import MatrixCell
from nwstep.domain.prefixed_item import PrefixedItem


class EdgeMatrix:
    def __init__(
        self,
        field: Field,
        interfaces_field: Field,
        categories: tuple[str, ...],
    ) -> None:
        self._field = field
        self._interfaces_field = interfaces_field
        self._categories = categories

    def check(self, items: list[str], interfaces: list[str]) -> None:
        identifiers: list[str] = []
        for interface in interfaces:
            identifier = PrefixedItem(interface).identifier
            if identifier is None:
                raise self._interfaces_field.refuse(
                    f"interface '{interface}' has no id; write it as 'I1: description'",
                    rejected=(interface,),
                    fault=Fault.SYNTAX,
                )
            identifiers.append(identifier)
        pairs = [
            f"{ident}.{category}"
            for ident in identifiers
            for category in self._categories
        ]
        covered: list[str] = []
        for item in items:
            try:
                cell = MatrixCell.parse(item)
            except ValueError as error:
                broken = PrefixedItem(item).identifier
                raise self._field.refuse(
                    f"matrix item '{item}' is not valid: {error}",
                    rejected=(item,),
                    missing=(broken,) if broken in pairs else (),
                    fault=Fault.SYNTAX,
                ) from None
            if cell.identifier not in pairs:
                raise self._field.refuse(
                    f"matrix item '{item}' names '{cell.identifier}', which is no interface and category pair",
                    rejected=(item,),
                    fault=Fault.UNKNOWN_NAME,
                )
            covered.append(cell.identifier)
        missing = tuple(pair for pair in pairs if pair not in covered)
        if missing:
            raise self._field.refuse(
                f"matrix lacks interface.category pair(s) {', '.join(missing)}: every interface needs every category",
                missing=missing,
                fault=Fault.COVERAGE,
            )
