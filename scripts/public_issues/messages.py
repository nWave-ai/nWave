"""The public wording the silence rule posts. The owner approved the thank-you text on 18 Nov 2026."""

from __future__ import annotations


THANK_YOU = (
    "Thank you for reporting this and for your patience. We have not heard back within "
    "36 hours of our reply, so we are closing this issue as fixed. If the problem is "
    "still there, or comes back, please comment here and it will reopen automatically. "
    "This message was posted automatically by nWave.ai."
)

REOPENED = (
    "This issue is reopened because the reporter replied. "
    "This message was posted automatically by nWave.ai."
)

REOPENED_BY_COMMENT = (
    "This issue is reopened because a new comment arrived. "
    "This message was posted automatically by nWave.ai."
)

REOPEN_BODIES = (REOPENED, REOPENED_BY_COMMENT)
