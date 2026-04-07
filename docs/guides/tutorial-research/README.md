# Tutorial: Evidence-Based Research

**Time**: ~10 minutes (5 steps)
**Platform**: macOS, Linux, or Windows
**Prerequisites**: Claude Code with nWave installed
**What this is**: A walkthrough of `/nw-research` -- nWave's evidence-based research command. You will ask it to compare pytest vs unittest, and get back a structured research document with citations, cross-referenced claims, and a confidence-rated recommendation.

---

## What You'll Build

A research document that compares two Python testing libraries -- pytest and unittest -- with evidence from multiple sources, cross-referenced claims, and a clear recommendation.

**Before**: You search "pytest vs unittest", read 4 blog posts with conflicting opinions, and pick whichever one the most recent article recommended.

**After**: You run one command and get a structured comparison backed by verified sources, with a confidence level on the recommendation so you know how much to trust it.

**Why this matters**: Technology decisions made on gut feeling or a single blog post create technical debt. `/nw-research` gathers evidence from multiple sources, cross-references claims (does Source A's claim hold up when checked against Source B?), and tells you how confident it is in the recommendation. You get a decision document you can share with your team, not a browser tab you will lose.

---

## Step 1 of 5: Open Claude Code (~1 minute)

Open Claude Code in any directory. The research command does not need a project -- it works anywhere.

```bash
claude
```

You should see the Claude Code prompt:

```
>
```

Verify nWave is available:

```
/nw-help
```

You should see a list of nWave commands, including `/nw-research`. If you see an error, nWave is not installed -- follow the [installation guide](../installation-guide/) first.

That is all the setup. No project, no dependencies, no configuration.

*Next: you will run your first research query.*

---

## Step 2 of 5: Run the Research Query (~1 minute to start, ~3-4 minutes to complete)

Type the following in Claude Code:

```
/nw-research "Should I use pytest or unittest for a new Python project? Compare developer experience, ecosystem, and learning curve."
```

The researcher agent will start gathering evidence. You will see phases scroll by:

```
● nw-researcher(Gathering evidence from multiple sources)
● nw-researcher(Cross-referencing claims across sources)
● nw-researcher(Synthesizing findings and rating confidence)
```

This takes 3-4 minutes. The agent is doing three things:

1. **Gathering evidence** -- Finding information from multiple sources about both libraries
2. **Cross-referencing** -- Checking whether claims from one source are supported or contradicted by others
3. **Synthesizing** -- Producing a structured comparison with a confidence-rated recommendation

> **AI output varies between runs.** Your research document will differ from the examples in this tutorial. The agent generates findings based on its knowledge, and phrasing will vary. What matters is the structure (sources, cross-references, recommendation with confidence), not the exact wording.

> **If the command does not start**: Run `/nw-help` to verify nWave is installed. If the command is not listed, reinstall nWave.

*Next: you will read the research output and understand its structure.*

---

## Step 3 of 5: Read the Research Document (~2 minutes)

After the agent finishes, you will see a structured research document. It follows this general shape:

```
Research: pytest vs unittest for a new Python project
======================================================

QUESTION: Should I use pytest or unittest for a new Python project?

SOURCES CONSULTED:
  1. [Source description and reference]
  2. [Source description and reference]
  3. [Source description and reference]
  ...

FINDINGS:

  Developer Experience:
    - pytest: [evidence with source citations]
    - unittest: [evidence with source citations]

  Ecosystem:
    - pytest: [evidence with source citations]
    - unittest: [evidence with source citations]

  Learning Curve:
    - pytest: [evidence with source citations]
    - unittest: [evidence with source citations]

CROSS-REFERENCES:
  - Claim: "[specific claim]"
    Supported by: Sources 1, 3
    Contradicted by: None
  - Claim: "[specific claim]"
    Supported by: Sources 2, 4
    Contradicted by: Source 1 (partially)
  ...

RECOMMENDATION: [recommendation]
CONFIDENCE: [High / Medium / Low] — [reason for confidence level]
```

**Your output will differ.** The specific sources, findings, and recommendation depend on the agent's investigation. What matters is:

- **Sources are listed** -- You can see where the evidence comes from
- **Claims are cross-referenced** -- You know which claims have broad support and which are disputed
- **Confidence is rated** -- The agent tells you how sure it is, and why

Two concepts in this step:

1. **Cross-referencing** -- The agent checks each claim against multiple sources. A claim supported by 3 sources is stronger than one from a single blog post. If sources contradict each other, the agent flags it.
2. **Confidence level** -- High means strong agreement across sources. Medium means some disagreement or limited evidence. Low means conflicting sources or insufficient data to decide.

*Next: you will verify the research quality yourself.*

---

## Step 4 of 5: Verify the Research (~2 minutes)

A research document is only useful if you can trust it. Check three things:

**1. Are the sources real?**

Look at the sources listed. The agent should cite specific documentation, well-known references, or established community knowledge. If a source seems vague ("various online discussions"), that is weaker evidence.

**2. Do the cross-references make sense?**

Pick one cross-referenced claim and think about it yourself. Does the claim match your own experience or knowledge? Cross-references where multiple sources agree are the strongest findings in the document.

**3. Does the confidence level match the evidence?**

If the agent says "High confidence" but only consulted 2 sources with no cross-referencing, that is a red flag. High confidence should come from multiple agreeing sources. Medium or Low confidence with an honest explanation is more trustworthy than inflated High confidence.

**What just happened?** You used `/nw-research` to generate a structured research document, then applied critical thinking to verify the output. The command does the heavy lifting of gathering and organizing evidence, but the final judgment is yours. This is the intended workflow -- the agent provides evidence, you make the decision.

> **If the document seems thin or generic**: Rephrase your question with more specifics. Compare: "pytest vs unittest" (vague) vs "Should I use pytest or unittest for a new Python project with 50+ modules, CI/CD on GitHub Actions, and a team of 3?" (specific). More context produces better research.

*Next: you will try a second query to see how research adapts to different questions.*

---

## Step 5 of 5: Try a Different Research Question (~2 minutes)

Run a second research query on a different topic to see how the output adapts:

```
/nw-research "What are the trade-offs between SQLite and PostgreSQL for a CLI tool that stores local user data?"
```

Watch for how the output structure stays consistent (sources, cross-references, confidence) while the content changes to match the new question.

Compare the two research documents:

- The **structure** is the same -- sources, findings, cross-references, recommendation, confidence
- The **depth** may differ -- some topics have more established consensus than others
- The **confidence level** may differ -- technology trade-offs with clear use-case boundaries often get higher confidence than subjective comparisons

### What You Built

You produced two evidence-based research documents:

1. **pytest vs unittest** -- A structured comparison for choosing a testing library
2. **SQLite vs PostgreSQL** -- A trade-off analysis for a specific use case

Both follow the same pattern: question, evidence gathering, cross-referencing, and a confidence-rated recommendation.

### When to Use `/nw-research`

- Choosing between two libraries or frameworks
- Evaluating whether to adopt a new technology
- Investigating best practices for a specific problem (e.g., "How should I handle database migrations in a microservices architecture?")
- Building a case for a technical decision to share with your team

### When NOT to Use It

- You already know the answer and just need a quick syntax reminder (use regular Claude Code instead)
- The question is opinion-based with no factual basis (e.g., "Is Python better than JavaScript?")
- You need real-time data like current pricing or availability (the agent uses its training knowledge, not live web searches)

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `/nw-research` does not start | Make sure nWave is installed. Run `/nw-help` to verify the command is listed. |
| Research output is too generic | Add more context to your question. Specify your use case, team size, constraints, and what you care about most. |
| Agent gives "High confidence" but evidence seems weak | This can happen with well-established topics where consensus is strong. Check the cross-references -- if multiple sources agree, the confidence may be justified even if the document is short. |
| Research takes more than 5 minutes | Complex questions with many dimensions take longer. This is normal for broad questions. Narrow your question to get faster results. |
| Agent does not cite specific sources | Rephrase to ask for a comparison with specific criteria: "Compare X and Y on performance, ecosystem size, and learning curve" gives better structure than "X vs Y". |
| You disagree with the recommendation | That is fine. The document gives you organized evidence to make your own decision. The recommendation is a starting point, not a verdict. |

---

**Last Updated**: 2026-02-18
