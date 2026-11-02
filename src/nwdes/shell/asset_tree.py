"""Read explicitly rooted brand assets without ambient discovery."""

from pathlib import Path

from nwdes.contracts import Built, refuse
from nwdes.shell.ports import AssetMissing, AssetUnreadable


def read_asset(root: str, relative: str) -> bytes | AssetMissing | AssetUnreadable:
    path = Path(root) / relative
    try:
        return path.read_bytes()
    except FileNotFoundError as exc:
        return AssetMissing(str(path), str(exc))
    except OSError as exc:
        failure = refuse(
            f"AssetUnreadable: {path}",
            str(exc),
            "Make the named installed asset readable.",
        )
        return AssetUnreadable(failure.refusal)


def decode_utf8(raw: bytes, path: str):
    try:
        return Built(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        failure = refuse(
            f"AssetUnreadable: {path}",
            str(exc),
            "Supply the named asset as readable UTF-8.",
        )
        return AssetUnreadable(failure.refusal)
