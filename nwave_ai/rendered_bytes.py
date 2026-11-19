"""The byte forms of a rendered text that an installer owns: its LF rendering and the full CRLF translation of it.

Pure: no filesystem effects. The installer writes a rendered text as its UTF-8 bytes, and a text-mode write on a platform
whose line ending is CRLF stores each line feed as CRLF. Both forms are the installer's own. Every other byte form is not.
"""

from __future__ import annotations

import hashlib


CR = b"\r"
LF = b"\n"
CRLF = b"\r\n"


def lf_of_crlf_translation(data: bytes) -> bytes | None:
    """Return the LF text whose full CRLF translation is data, or None when data is not exactly such a translation.

    The text must hold no carriage return, so a bare CR, a bare LF or a mixed line ending gives None.
    """
    text = data.replace(CRLF, LF)
    if CR in text or text.replace(LF, CRLF) != data:
        return None
    return text


def owns_digest(data: bytes, recorded_sha256: str | None) -> bool:
    """Return True when data is nWave's own by its recorded digest.

    Own means: the sha256 of data is recorded, or data is the full CRLF translation of a text whose sha256 is recorded.
    A recorded digest of None owns nothing.
    """
    if recorded_sha256 is None:
        return False
    if hashlib.sha256(data).hexdigest() == recorded_sha256:
        return True
    text = lf_of_crlf_translation(data)
    return text is not None and hashlib.sha256(text).hexdigest() == recorded_sha256
