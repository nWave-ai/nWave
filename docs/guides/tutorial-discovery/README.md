# Tutorial: From Idea to Validated Problem

**Time**: ~15 minutes (7 steps)
**Platform**: macOS or Linux (Windows: use WSL)
**Prerequisites**: Python 3.10+, Claude Code with nWave installed, [Tutorials 1-3](../TUTORIALS.md) completed
**What this is**: An interactive walkthrough of `/nw-discover` -- nWave's product discovery command. You will validate a product idea before writing any code.

---

## What You'll Build

A validated (or invalidated) product concept -- with evidence, not opinions.

**Before**: You have an idea for a "bookmark manager CLI tool" and a gut feeling that developers need it.

**After**: You have a structured discovery document that tells you whether the problem is real, how big it is, and whether to proceed, pivot, or stop -- all based on evidence from real developer behavior, not hypothetical questions.

**Why this matters**: The most expensive code is code that solves the wrong problem. Discovery takes 15 minutes. Building the wrong thing takes weeks.

---

## Step 1 of 7: Set Up the Project (~2 minutes)

Create a project directory for your discovery work:

```bash
mkdir bookmark-cli && cd bookmark-cli
git init
mkdir -p docs
```

You should see:

```
Initialized empty Git repository in .../bookmark-cli/.git/
```

Create a brief project description that gives the discoverer context. This is optional but speeds up the process:

```bash
cat > docs/project-brief.md << 'EOF'
# Bookmark CLI

A command-line tool for developers to save, tag, and search bookmarks
without leaving the terminal. Aimed at developers who use the terminal
as their primary workspace.

## Initial Assumptions
- Developers lose track of useful links (docs, Stack Overflow, blog posts)
- Browser bookmarks are disorganized and hard to search
- A CLI tool would fit the developer workflow better than a browser extension
EOF
```

Verify the file was created:

```bash
cat docs/project-brief.md
```

You should see the project brief you just wrote.

> **If you see "No such file or directory"**: Make sure you are inside the `bookmark-cli` directory. Run `pwd` to check.

Commit the initial setup:

```bash
git add -A && git commit -m "chore: initial project with discovery brief"
```

You should see:

```
[main (root-commit) ...] chore: initial project with discovery brief
```

*Next: you will start the discovery session and meet Scout, the product discoverer agent.*

---

## Step 2 of 7: Launch Discovery (~1 minute)

Open Claude Code and launch the discovery command:

```bash
claude
```

Then type this Claude Code command (not a terminal command):

```
/nw-discover bookmark-cli
```

> **AI output varies between runs.** Your conversation with Scout will differ from the examples below. That is expected -- Scout adapts to your specific answers. What matters is the structure of the conversation (questions about past behavior, assumption tracking), not the exact wording.

Scout (the product discoverer agent) will introduce itself and start Phase 1: Problem Validation. You will see something like:

```
I'm Scout, your Product Discovery Facilitator. Let's validate whether
bookmark-cli solves a real problem before writing any code.

I've read your project brief. You've listed 3 assumptions. Let's test
the riskiest one first:

"Developers lose track of useful links."

When did YOU last lose a link you needed? Walk me through what happened.
```

**What just happened?** Scout read your `docs/project-brief.md`, identified your assumptions, and started with the highest-risk one. Notice the question asks about a specific past event -- not "Would you use a bookmark tool?" That distinction matters, and the next step explains why.

*Next: you will learn why Scout asks questions this way.*

---

## Step 3 of 7: Understand the Method (~1 minute)

Before you answer Scout's first question, take a moment to understand the two ideas driving this conversation:

1. **Assumptions vs. facts**: Your project brief contains three assumptions. Until you test them with evidence, they are guesses -- not features to build. Scout's job is to turn assumptions into validated facts (or invalidated ones).
2. **Mom Test questioning**: Scout asks about specific past experiences ("When did you last..."), not hypothetical preferences ("Would you use..."). This technique (from Rob Fitzpatrick's "The Mom Test") prevents false validation. Past behavior predicts future behavior. Opinions do not.

These two ideas explain everything Scout does: it identifies your assumptions, then tests each one by asking about real past behavior -- never hypothetical intent.

*Next: you will answer Scout's questions and watch it track your assumptions.*

---

## Step 4 of 7: Work Through the Interview (~5 minutes)

Answer Scout's questions honestly based on your real experience. There are no wrong answers -- the goal is evidence, not validation.

Here is an example exchange (yours will differ):

**Scout asks about past behavior:**
```
When did you last lose a link you needed? Walk me through what happened.
```

**You answer honestly** (use your real experience):
```
Last week I was looking for a Python packaging guide I'd read months ago.
I spent 10 minutes searching browser history and bookmarks before finding
it buried in a folder I forgot about.
```

**Scout digs deeper:**
```
Good -- that's a specific example. Two follow-ups:

1. How often does this happen? Weekly? Monthly?
2. What did you try before searching browser bookmarks? (Slack search?
   Google again? Ask a colleague?)
```

**You answer:**
```
Maybe twice a month. I usually Google again first -- it's faster than
searching my own bookmarks, which says something about how useless they are.
```

Scout will continue for 3-5 questions, then summarize what it learned. You will see it update an assumption tracker:

```
Assumption Tracker Update:

| # | Assumption                              | Risk | Status     | Evidence |
|---|-----------------------------------------|------|------------|----------|
| 1 | Developers lose track of useful links   | High | Testing    | 1 signal: bi-monthly occurrence, Google preferred over own bookmarks |
| 2 | Browser bookmarks are disorganized      | Med  | Untested   | — |
| 3 | CLI tool fits developer workflow better  | High | Untested   | — |
```

> **Your tracker will look different.** The structure (numbered assumptions with risk scores and evidence status) is what matters, not the exact content.

After the initial interview, Scout will ask about other developers' behavior -- not just yours. It needs 5+ signals before making any recommendation:

```
You've described your own experience. Now I need to broaden the sample.

Do you have observations of OTHER developers struggling with this?
Team Slack threads? Questions in standups? Anything specific.
```

Answer based on what you have actually observed (not what you think might happen).

> **If Scout asks a question you cannot answer**: Say so honestly. "I don't have data on that" is a valid and useful answer. Scout will note the gap and suggest how to fill it.

*Next: you will see Scout evaluate the evidence and reach a decision gate.*

---

## Step 5 of 7: Reach the Decision Gate (~3 minutes)

After gathering enough evidence, Scout evaluates whether to proceed, pivot, or stop. You will see it run a gate evaluation:

```
Gate G1 Evaluation: Problem Validation

| Criteria                    | Target | Actual        | Status |
|-----------------------------|--------|---------------|--------|
| Signals collected           | 5+     | 5             | PASS   |
| Problem confirmation rate   | >60%   | 80% (4 of 5)  | PASS   |
| Frequency                   | Weekly+| Bi-monthly    | WARN   |
| Current workaround spending | >$0    | Time only     | WARN   |
| Emotional intensity         | High   | Moderate      | WARN   |

Recommendation: PROCEED WITH CAUTION

The problem exists but is low-frequency and low-intensity. Developers
DO lose links, but it's an annoyance, not a crisis. Consider:
- Is there a higher-pain sub-problem? (e.g., losing API reference
  links during active debugging)
- Would the solution need to be zero-friction to justify bi-monthly use?
```

> **Your gate evaluation will differ.** Scout's recommendation depends entirely on what you told it. You may see PROCEED, PIVOT, or even KILL. All three are valid outcomes -- the point is evidence-based decision-making.

Three possible outcomes at the gate:

| Outcome | What it means | What you do next |
|---------|--------------|-----------------|
| **Proceed** | Evidence supports the problem. Move to opportunity mapping. | Scout guides you to Phase 2 |
| **Pivot** | Problem exists but differs from your assumption. Reframe. | Scout helps you redefine the problem |
| **Kill** | Evidence does not support the problem. Stop here. | You saved weeks of wasted effort |

**What just happened?** Scout applied the same rigor to your product idea that nWave's TDD pipeline applies to code. Instead of "write code, hope it works," you did "test assumption, check evidence." Both follow the same principle: validate before you build.

*Next: you will review the discovery artifacts Scout created.*

---

## Step 6 of 7: Review the Artifacts (~2 minutes)

Scout saves its findings to `docs/feature/bookmark-cli/discover/`. Check what was created:

```bash
ls docs/feature/bookmark-cli/discover/
```

You should see:

```
problem-validation.md
wave-decisions.md
```

> **You may see additional files** like `opportunity-tree.md`, `lean-canvas.md`, or `interview-guide.md` depending on how far your discovery progressed. That is expected.

Open the problem validation document:

```bash
cat docs/feature/bookmark-cli/discover/problem-validation.md
```

You will see a structured document containing:

- **Problem statement** in customer words (not your original assumption)
- **Evidence summary** with specific signals from your interview
- **Assumption tracker** with risk scores and validation status
- **Gate evaluation** with the proceed/pivot/kill recommendation
- **Next steps** based on the recommendation

> **Your document content will differ from any example.** The structure (sections listed above) is what matters.

Commit the discovery artifacts:

```bash
git add -A && git commit -m "docs: problem validation from discovery session"
```

You should see:

```
[main ...] docs: problem validation from discovery session
```

> **If `docs/feature/bookmark-cli/discover/` does not exist**: Scout may not have reached the point of writing artifacts. This happens if the conversation was very short. Run `/nw-discover bookmark-cli` again -- it picks up where it left off.

*Next: a recap of what you learned and where to go from here.*

---

## Step 7 of 7: What Just Happened (~1 minute)

You started with an idea ("bookmark manager CLI tool") and three untested assumptions. Scout guided you through evidence-based validation:

1. **Assumptions identified** -- Your gut feelings became testable hypotheses with risk scores
2. **Past behavior questioned** -- "When did you last..." instead of "Would you use..." prevents false validation
3. **Evidence collected** -- Specific signals, not opinions, drove the evaluation
4. **Decision gate evaluated** -- Objective criteria determined whether to proceed, pivot, or stop

### What You Didn't Have to Do

- Build a prototype to find out if the problem was real
- Survey 100 developers with a Google Form
- Spend weeks coding before discovering nobody needs it
- Guess whether your idea was good

### The Three Outcomes Are All Wins

| Outcome | Why it's a win |
|---------|---------------|
| **Proceed** | You have evidence the problem is worth solving. Confidence to invest. |
| **Pivot** | You found a better problem. Discovery redirected your effort. |
| **Kill** | You saved weeks of work on the wrong thing. That is the highest-value outcome. |

---

## Next Steps

- **[Tutorial 5: Exploring Design Directions](../diverge-wave-guide/)** -- If Scout said "proceed" and you have a greenfield project or want to explore multiple approaches, run `/nw-diverge` to generate and evaluate design directions before requirements
- **[Tutorial 6: Requirements and UX Journey](../tutorial-discuss/)** -- If you already know the approach, skip DIVERGE and go straight to `/nw-discuss` to turn your validated problem into user stories with acceptance criteria
- **Run discovery on your own idea** -- Pick a feature you have been meaning to build. Run `/nw-discover` and see if the problem holds up under scrutiny
- **Re-read your project brief** -- Compare your original assumptions to what the evidence showed. How many survived?

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Scout does not start after `/nw-discover` | Make sure nWave is installed. Run `/nw-help` to verify. |
| Scout asks too many questions | Say "let's evaluate the gate now" -- Scout will run the evaluation with whatever evidence exists. |
| No `docs/feature/bookmark-cli/discover/` directory after the session | Scout writes artifacts at phase transitions. If you ended the session early, run `/nw-discover bookmark-cli` again to resume. |
| Scout recommended KILL and you disagree | That is fine -- Scout advises, you decide. But document why you are overriding the evidence. |
| Want to start discovery fresh | Delete `docs/feature/bookmark-cli/discover/` and run `/nw-discover` again. |

---

**Last Updated**: 2026-02-17
