---
name: nw-rigor
description: Use when the user wants to see or change how much rigor a project gets (review rounds, examine level), which provider/model a role uses, or whether readable documents are written. The LLM reads the current settings, asks only the missing choices in plain words, and runs `nwave-ai rigor` or `nwave-ai model set` itself. Never derives a model from a competence label.
user-invocable: true
argument-hint: '[review rounds, examine level, provider, model, scope, optional role]'
---

# NW-RIGOR

The user collaborates with you. You run every command; the user never types
terminal commands. nwdes does not execute models, and the CLI neither maps
competence to a model, checks availability, nor falls back.

## 1. Read what is already set

Run `nwave-ai rigor --show` (read only) and read its values and their sources.
Also read the project `.nwave/config.json` and the global `.nwave/config.json`
(under a valid absolute `NWAVE_AGENTS_HOME`, otherwise the home directory).
Reuse anything the user already said in this conversation; never ask them to
repeat a known value or type an identifier already available.

## 2. Ask once, in one batch

Ask ONE batched question set in plain words (short sentences, everyday words),
not one round trip per item. Say what each item changes for the user's work.
Keep tool names (option names, `producers`, `reviewers`, `executors`, role
names, `charter`, `slice`, `lane`, `handoff`) in your commands only, never in
a sentence the user reads. Cover only what is missing or what the user wants
to change. Each item gives: the current value and source as the suggested
answer, the cost and benefit of the options, and your recommendation. End with
one direct question ("keep these, or change which?").

1. **Review rounds (1-5).** How many times a second person, not the author,
   may check the same piece of work. Cost: one more check per round. Benefit:
   fewer mistakes stay unseen. Too few rounds can miss mistakes; many rounds
   can keep finding small things and never stop.
2. **Examine level.** A final check of the finished work, by someone who has
   not read the code; it finds what automatic tests miss. Explain "examination"
   as one such check and "repair round" as one chance to fix what it found.
   Present the tool's own text, copied here once and pinned by a test:

   | Level | gives | not covered at this level |
   |---|---|---|
   | `quick` | 1 examination, no repair round | any repair round |
   | `standard` (default) | 2 examinations, 1 repair round | more than 1 repair round |
   | `extended` | 3 examinations, 2 repair rounds | more than 2 repair rounds |

   Not covered at any level: security, load or checks on other machines.
   The tool also says: a row not examined is never green. A longer level is not safer.
3. **Which AI model does which kind of work.** Say it as: a stronger model for
   hard work, a faster one for routine work, for all work of one kind or for one
   named helper. Offer the model already in effect or known from the config or
   the conversation; keeping it is the default. Map the answer to
   `--model-set` with a group (`producers`, `reviewers`, `executors`) or an
   exact published role name.
4. **Readable summary pages.** A web page in plain language, for people who do
   not read code, written when a piece of work is finished: yes or no. When
   yes, also the language (a code such as `en`, `de`, `it`).
5. **Other AI tools on this computer.** Whether they should also get the model
   choices. Writing changes files in the user's home folder; a backup copy
   is kept next to each. Two tools (`codex`, `devin`) cannot take a model per
   kind of work and refuse. Default: change nothing.

Rounds and levels bound the rework loops. A finding still open at the limit
returns to its owner; reaching the limit is never an approval and nothing
passes silently.

## 3. Apply with ONE command

The command takes every chosen value together. State it before running, run it,
report the result, then run `nwave-ai rigor --show` and show the new values.
Use `current` or `keep` for what does not change, and `--yes`: the user's
answers are the confirmation. Give each option once.

```bash
nwave-ai rigor --yes --review-rounds 3 --examine-level extended --models keep --documents yes --document-language en --hosts keep
```

That example sets 3 rounds, the extended level and English documents, and
changes no models or host file. Adapt only the values. The options:

- `--show`: print the values in effect; writes nothing.
- `--yes`: the user's answers are the confirmation.
- `--review-rounds`: `1` to `5`, or `current`.
- `--examine-level`: `quick`, `standard`, `extended`, or `current`.
- `--models`: `keep`; or use `--model-set` once per target, as
  `--model-set reviewers=PROVIDER/MODEL`.
- `--documents`: `yes`, `no` or `keep`; `--document-language LANG` only with `yes`.
- `--hosts`: host names separated by commas, `none` or `keep`.

After a refusal, report its WHAT/WHY/HOW and ask the user; never substitute
another value, provider, model or scope.

## Provider/model selection

Model facts for native-host role invocation are set per target: `--model-set`
above (groups `producers`, `reviewers`, `executors`, or a published role name)
or, for the default or one role, `nwave-ai model set`:

| Scope and target | Command |
|---|---|
| Global default | `nwave-ai model set --provider PROVIDER --model MODEL` |
| Current-project default | `nwave-ai model set --provider PROVIDER --model MODEL --project` |
| Global published-role override | `nwave-ai model set --provider PROVIDER --model MODEL --role ROLE` |
| Current-project published-role override | `nwave-ai model set --provider PROVIDER --model MODEL --role ROLE --project` |

- Suggest the effective current pair (project role override beats global
  default) with its source; the user accepts or changes it.
- A requested competence level helps the user choose a pair; the CLI has no
  competence profile or mapping. Keep the current pair until the user selects
  another.
- `PROVIDER` is `codex` or `claude`; `MODEL` the accepted exact string; `ROLE`
  only an exact published role name. Never invent an identifier, a competence
  mapping or a fallback; the stored value is not checked, so a wrong name shows
  only when the role runs.
