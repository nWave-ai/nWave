Card: {card}

# {title}

## The problem

{problem}

## What to deliver

{deliver}

## Owner decisions

{decisions}

## Acceptance

{acceptance}

## Limits and process

Do not read or edit any file outside your lane, except scratch under {scratch}. Use a folder named after your lane there. That folder never contains the word host.

Use your own TMPDIR for every test run and for git commit.

Never use --no-verify.

Do not run the whole suite. Run one pytest process at a time under flock ~/.cache/nwave/exp3-pytest.lock, and run the tests that cover the files you touch.

Generated delivery documents carry the machine's home path (known defect, card t-0512). Redact them with one literal rule, applied by a script kept in your scratch folder: the home folder string becomes ~, the scratch prefix likewise, and the account name becomes <account>. Never edit them by hand. Search the staged files for /home/, the account name and private product names before you commit.

Commit through all hooks, with the conventional commit type that the acceptance section names. Never use BREAKING CHANGE.

A commit that changes only documents, evidence or records is docs or chore, never feat, fix, perf or refactor; a commit that changes only tests is test.

The lane must have no uncommitted file before you stop.

## Evidence

Evidence of this delivery lives in the feature folder docs/feature/<feature>/evidence/, where <feature> is the feature id the delivery declares, and is never at the repository root: two deliveries that write a file of the same name there collide on rebase.

The RED evidence is a real JUnit report of a run of the new tests failing on the base commit, kept in docs/feature/<feature>/evidence/. Name the base commit and the candidate commit beside it in the committed record.

Every file you commit has content. No committed evidence file is empty, and a placeholder never stands in for evidence.

After you commit, check the files this delivery adds with the command below. It prints each added file that is empty, and nothing when none is. Put <base> in place of the base commit, the commit the workspace records in baseline.json:

git diff --diff-filter=A --name-only <base>..HEAD | while read f; do test -s "$f" || echo "EMPTY $f"; done

Show the output of that command in the closing record. It must print nothing.

## Outputs you owe in the closing record

- Name the tier of each new test: unit (at most 10 ms) or integration (within seconds). A test you did not run has no tier claim.
- The test-cost receipt, kept in docs/feature/<feature>/evidence/test-cost.md: for each new test file, n, median and max over nine runs in a row, and the load average read before the first run with cat /proc/loadavg.
- A list of what was not verified, one line each.

Stop at READY FOR REVIEW with the full commit hash read from git log. Never take it from memory or from a report. After that, do not edit the lane until the root answers.
