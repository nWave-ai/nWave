"""The schema versions nwstep no longer ships, each identified by the SHA-256 of its exact bytes.

Pure: bytes in, name out. A workspace or a source whose schema is one of these is refused where it is read.
Matching bytes, not header words, because dynamic-v1 has no version word and dynamic-v2b shares the header of dynamic-v2.
"""

from __future__ import annotations

import hashlib


RETIRED_SCHEMA_DIGESTS = {
    "dynamic-v1": "5cab19de912ad55603ec69aa83d91b398d043b32a0b11c5571477fa115aafae3",
    "dynamic-v2": "e179024a50b177f3d7ca543767e242e83d39e7940ec9d051949e0e59c672c35a",
    "dynamic-v2b": "0636119d2f8305fe556cdea7e29f477fae507bfb33b221151ae6bf9c158181c5",
    "dynamic-v2c": "639763ed32577395210c4b25d329bd71cc0264b0d1e3bc312c7ca3ed33a862c0",
    "dynamic-v2d": "50053c2f9f931df2a1c035ce2b8567225f4219416e431c20ef6bacd9882dd620",
    "dynamic-v2e": "66d54a7453878f0c3d9d7fe46fdfbf75d37d6b0b1cac2a44bad068cb21f4637e",
    "dynamic-v3e": "247506ea531a8562472df663ef6e27288e0cb40c0079da8058910fc7849ef305",
    "dynamic-v5": "7c458f950b9826121b12344b7279bebbdb2065ad79c325fef38c5f3fac17b4b6",
    "dynamic-v6": "2736358d511e09a2ba5e5294de66b01a64f27dd67a02ae2cffe15fa3f29ed797",
    "dynamic-v7": "48ba490aad83f0c7b7416f9137a40fbef795872b5f752874d35f77042ecf2438",
    "dynamic-v8": "06c8dcd5727ea0347ccd02f0f6a7a68249bcbfd70ef7bbc9cd780d1097bdf444",
}


def retired_name(content: bytes) -> str | None:
    """The name of the retired schema whose exact bytes these are, or None when they match no retired schema."""
    digest = hashlib.sha256(content).hexdigest()
    return next(
        (name for name, retired in RETIRED_SCHEMA_DIGESTS.items() if retired == digest),
        None,
    )
