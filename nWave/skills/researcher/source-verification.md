---
name: source-verification
description: Source reputation tiers, cross-referencing methodology, bias detection, and citation format requirements
---

# Source Verification

## Source Reputation Tiers

Validate every source against `nWave/data/config/trusted-source-domains.yaml` before citation.

| Tier | Reputation Score | Examples | Verification Needed |
|------|-----------------|----------|-------------------|
| High | 1.0 | Academic (*.edu, arxiv.org, ieee.org), Official (*.gov, w3.org, ietf.org), Technical docs (developer.mozilla.org), Open source foundations (apache.org, cncf.io) | Standard citation |
| Medium-High | 0.8 | Industry leaders (martinfowler.com, stackoverflow.com, infoq.com, thoughtworks.com) | Cross-reference with 1+ high-tier source |
| Medium | 0.6 | Community platforms (medium.com from verified experts, dev.to, hashnode.com) | Author verification + 3-source cross-reference |
| Excluded | 0.0 | Unverified blogs (*.blogspot.com, wordpress.com), quora.com, pastebin.com | Reject. Log warning and find alternative |

## Cross-Referencing Methodology

1. **Identify the claim**: Extract the specific assertion to verify
2. **Find independent sources**: Locate 2+ additional sources that are not citing each other (avoid circular references)
3. **Verify independence**: Confirm sources have different authors, publishers, or organizations
4. **Compare claims**: Check if sources agree on substance (minor wording differences are fine)
5. **Document result**: Record cross-reference status per finding (verified / partially verified / unverified)

### Circular Reference Detection
- If Source B cites Source A, they count as one source, not two
- If multiple sources all reference a single original study, cite the original
- Use primary sources where possible over secondary interpretations

## Bias Detection Checklist

Before citing any source, evaluate:

1. **Commercial interest**: Is the source selling a product or service related to the claim?
2. **Sponsorship**: Is the content sponsored or funded by a stakeholder?
3. **Conflict of interest**: Does the author benefit from a particular conclusion?
4. **Geographic/cultural bias**: Are perspectives limited to a single region?
5. **Temporal bias**: Is the publication date distribution skewed to a specific era?
6. **Cherry-picking**: Does the source acknowledge contradictory evidence?
7. **Logical fallacies**: Correlation presented as causation, appeal to authority without evidence

When bias is detected, note it in the Source Analysis table and reduce confidence accordingly.

## Citation Format

Use numbered citations in the research document:

```
[1] {Author/Organization}. "{Title}". {Publication/Website}. {Date}. {Full URL}. Accessed {YYYY-MM-DD}.
```

### Required Metadata Per Source
- Source URL
- Domain
- Access date
- Reputation score (from tier table)
- Verification status (cross-verified / single-source / unverified)

### Paywalled or Restricted Sources
- Mark clearly with "[Paywalled]" or "[Restricted Access]"
- Provide the URL anyway for reference
- Find an open-access alternative when possible
- Note access limitations in Knowledge Gaps section
