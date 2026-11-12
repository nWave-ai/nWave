# Read architecture diagrams and the readable brief

This guide shows how to turn on the readable output, and how to check that a diagram is easy to read.
It also explains what the documentarist does and does not do.
It is a how-to guide with a short explanation at the end.

## Before you start

You need:

- A project with nWave installed.
- The `nwave-ai` command.
- A terminal in the root of your repository.

## The readable output: on by default

1. Run the rigor command and answer the documents question with `yes`:

   ```bash
   nwave-ai rigor
   ```

   The command asks if you want a readable brief. When you answer `yes`, it asks for the language.

2. To skip the questions, give the answers as options:

   ```bash
   nwave-ai rigor --yes --models keep --review-rounds current --documents yes --document-language en --hosts keep
   ```

3. Check the result. This command writes nothing:

   ```bash
   nwave-ai rigor --show
   ```

   After steps 1 or 2 the project file holds your answer, so the line reads `documents: yes, language en (project)`. It shows the readable output is on, from that choice.

### Checking the default

The default applies only when no level declares the setting. To see it, run `nwave-ai rigor --show` in a repository whose `.nwave/config.json` has no `documents.readable_brief`, before steps 1 or 2. The line then reads `documents: yes, language en (built-in default)`. This check writes nothing.

A project or global `enabled: false` wins over the default. The line then reads `documents: no (project)` or `documents: no (global)`.

The setting is `documents.readable_brief` in `.nwave/config.json`. Answer `no` to turn it off.
Because the readable output is on by default, a diagram without its `%% alt:` line, or one with more than 25 distinct nodes, refuses the run until it is fixed. The check covers every brief the command writes while the setting is on: the charter, the design, the product owner's output, the project brief and the overview, with or without HTML pages. The refusal names each broken diagram and the brief file it is in, and writes nothing. Answering `no` keeps the earlier behaviour: no check, and diagrams stay code.
See the [rigor entry](../reference/cli.md#nwave-ai-rigor) for every option.

## What the readable output contains

When the setting is on, the product page of each feature (`brief.html`) shows the request, the work and the promises as plain paragraphs. Other pages keep their code blocks; they are still checked against the same diagram rule.

The roles also do more work for the reader:

- The product owner, the architect and the platform architect write each decision with a short title and a reason.
- The architect draws diagrams under 12 rules (see below).
- The documentarist asks the owners one round of questions, then shows their decisions with their ids.

The HTML product page shows each Mermaid diagram as its declared description, a paragraph above a collapsed `Diagram source` block, and declares the configured language as the page `lang`. A diagram that breaks a rule refuses the whole run, so no page is written with a diagram missing its description. Read the description paragraph in the page or in the Markdown brief.

## What an accessible diagram is

An accessible diagram works for a person who cannot see the colors, cannot see the picture, or cannot read small text.
Each rule can be checked in the diagram source. You do not need to render it.

| Rule | In plain words |
|---|---|
| R1 | The diagram has a title inside its block. |
| R2 | One to three sentences above it start with "This diagram shows:". |
| R3 | The block has at most 25 nodes. This limit is provisional. |
| R4 | A node label has at most 40 characters and 2 line breaks. |
| R5 | The reading direction is standard and stated. |
| R6 | Color is never the only signal. Shape, dash style or label also differ. |
| R7 | Each color pair has enough contrast. |
| R8 | A legend explains the styles. |
| R9 | Groups of more than 8 nodes have human names. |
| R10 | Edge labels are short and not repeated more than 4 times. |
| R11 | Acronyms and ids are expanded once. |
| R12 | One C4 level per block. |

The `nw-diagram` skill holds the exact wording. This guide only summarizes it.
Old diagrams in `docs/archive` are not rewritten. The rules apply to new and regenerated diagrams.

## Check a diagram yourself

1. Open the Mermaid source.
2. Find the title. For a C4 diagram it is a `title` line. For other types it is `title:` in the first lines.
3. Read the sentence above the block. It must say what the diagram shows.
4. Count the nodes. If you find more than 25, ask for a split.
5. Look for `classDef` or `style`. If you find one, look for a legend.

Ask the architect to fix each failed rule. Name the rule id, for example: "R3: split the diagram".

## What the documentarist does

When the readable output is on, the documentarist (Quill):

- checks every diagram against R1-R12 and lists each failed rule with a fix;
- reads the decisions that the product owner, architect and platform architect recorded;
- sends ONE message with numbered questions to each owner at the end of analysis;
- shows each decision in the readable document with its id, title and reason.

The questions cover a missing title, a missing reason, a choice that a lay reader cannot follow, and a failed diagram rule.
The owner answers once. The owner corrects the decision at its source and replies with the id. The round does not repeat. A question without an answer stays open in the document.

## What the documentarist does not do

- It does not write or change a decision. Only the owner does.
- It does not fill a missing reason from its own reading.
- It does not make product, architecture or operations choices.
- It does not run a second round.

## Use it in the interactive dynamic route

In `/nw-dynamic interactive`, the host reads `documents.readable_brief`. When it is on, the host adds a readable-output block to the request. The executor then reads `nw-diagram` and `nw-doc-as-artifact`. After the design step, the host runs the one documentarist round. Auto mode does not do this.
No tool checks that the executor follows the block.

## Explanation: why these rules exist

A diagram can be correct and still be unreadable. A screen reader gets the raw Mermaid source, not a picture. A reader with low vision cannot use a pale fill with a pale line. A reader who is new to the project cannot decode `E1` or `SYS-4`.

The rules are small on purpose. Each one is a fact in the source text, so a reviewer can check it in seconds.
The limit of 25 nodes is a starting value. It can change when real diagrams show a better number.

The documentarist only presents decisions because a decision has an owner. If the writer of the document could add a reason, the document could say something that nobody chose.
