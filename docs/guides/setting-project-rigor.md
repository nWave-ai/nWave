# Set the review rounds and examine level for a project

This guide shows how to see and change how much checking a project gets. You do not type anything: ask your assistant, and it reads the current settings, asks you only what is missing, and sets the values for you.

## Before you start

You need a project with nWave installed and your assistant working in it.

## What the two settings mean

**Review rounds (1 to 5)** is how many times a second person, not the author, may check the same piece of work. Each round costs one more check. Few rounds can leave mistakes unseen. Many rounds can keep finding small things and never stop. When a problem is still open at the limit, the work stops and the problem goes back to the person who made that part. Reaching the limit is never an approval.

**Examine level** is a final check of the finished work, by someone who has not read the code. It finds what automatic tests miss. An "examination" is one such check. A "repair round" is one chance to fix what it found.

| Level | gives | not covered at this level |
|---|---|---|
| `quick` | 1 examination, no repair round | any repair round |
| `standard` (default) | 2 examinations, 1 repair round | more than 1 repair round |
| `extended` | 3 examinations, 2 repair rounds | more than 2 repair rounds |

Not covered at any level: security, load or checks on other machines. The tool also says: a row not examined is never green. A longer level is not safer.

## Ask your assistant to change them

Say what you want, for example "use 3 review rounds and the extended examine level". The assistant reads the current values, asks you in one batch about anything still missing (review rounds, examine level, which AI model does which work, readable summary pages, other AI tools on this computer), tells you the one command it will run, runs it, and shows you the new values.

## What the assistant runs for you

To read the values, the assistant runs this command, which writes nothing:

```bash
nwave-ai rigor --show
```

Each line ends with its source: `project`, `global` or `built-in default`. To change them, the assistant runs one command that carries every choice and leaves the other values as they are. For the example above it runs:

```bash
nwave-ai rigor --yes --models keep --review-rounds 3 --examine-level extended --documents keep --hosts keep
```

These commands are shown so you can see what changed; you do not type them. After the change the assistant shows `--show` again: the review rounds and the examine level carry your values with source `project`.

Models, documents and hosts are covered in [Assigning models to roles](./assigning-models-to-roles.md) and [Read architecture diagrams and the readable brief](./readable-brief-and-diagrams.md). Every option is in the [rigor entry](../reference/cli.md#nwave-ai-rigor).
