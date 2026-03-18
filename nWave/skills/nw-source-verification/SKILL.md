---
name: nw-source-verification
description: Source reputation tiers, cross-referencing methodology, bias detection, and citation format requirements
disable-model-invocation: true
---

# Source Verification

## Source Reputation Tiers

Validate every source against the trusted source domains provided via prompt context.

| Tier | Score | Examples | Verification |
|------|-------|---------|-------------|
| High | 1.0 | Academic (*.edu, arxiv.org, ieee.org), Official (*.gov, w3.org, ietf.org), Tech docs (developer.mozilla.org), OSS foundations (apache.org, cncf.io) | Standard citation |
| Medium-High | 0.8 | Industry leaders (martinfowler.com, stackoverflow.com, infoq.com) | Cross-ref with 1+ high-tier |
| Medium | 0.6 | Community (medium.com verified experts, dev.to, hashnode.com) | Author verification + 3-source cross-ref |
| Excluded | 0.0 | Unverified blogs (*.blogspot.com, wordpress.com), quora.com, pastebin.com | Reject, log warning, find alternative |

## Cross-Referencing Methodology

1. **Identify** the specific assertion to verify
2. **Find** 2+ independent sources not citing each other (avoid circular refs)
3. **Verify independence**: different authors, publishers, organizations
4. **Compare**: agree on substance (minor wording differences OK)
5. **Document**: verified / partially verified / unverified per finding

### Circular Reference Detection
- Source B cites Source A = one source, not two
- Multiple sources referencing single study = cite the original
- Prefer primary over secondary sources

## Bias Detection Checklist

Evaluate before citing:
1. **Commercial interest**: selling related product/service?
2. **Sponsorship**: sponsored/funded content?
3. **Conflict of interest**: author benefits from conclusion?
4. **Geographic/cultural bias**: limited to single region?
5. **Temporal bias**: publication dates skewed to specific era?
6. **Cherry-picking**: contradictory evidence acknowledged?
7. **Logical fallacies**: correlation as causation, authority without evidence

When bias detected: note in Source Analysis, reduce confidence.

## Citation Format

```
[1] {Author/Organization}. "{Title}". {Publication/Website}. {Date}. {Full URL}. Accessed {YYYY-MM-DD}.
```

### Required Metadata Per Source
Source URL | Domain | Access date | Reputation score (from tiers) | Verification status

### Paywalled or Restricted Sources
Mark "[Paywalled]"/"[Restricted Access]" | Provide URL | Find open-access alternative | Note in Knowledge Gaps
