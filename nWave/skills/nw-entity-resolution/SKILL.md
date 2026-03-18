---
name: nw-entity-resolution
description: Cross-platform identity matching techniques for resolving entities across multiple OSINT sources, with confidence scoring framework, blocking strategies, and LLM-assisted validation.
disable-model-invocation: true
---

# Entity Resolution

## When to Apply

Apply entity resolution whenever data about the same entity arrives from 2+ sources. Common scenarios:
- Same person name on GitHub, LinkedIn web profile, patent database, publication search
- Same company name across registries, Crunchbase, news articles (with variations in legal form)
- Cross-referencing board members across multiple company filings

## Company Name Normalization

Before matching, normalize company names:

1. Strip legal suffixes: Inc, Corp, LLC, Ltd, GmbH, S.r.l., S.p.A., SA, SAS, AG, plc, NV, BV
2. Normalize abbreviations: "Intl" -> "International", "Tech" -> "Technology", "Sys" -> "Systems"
3. Lowercase, strip punctuation, collapse whitespace
4. Handle trade names vs legal names: "Google" vs "Alphabet Inc.", "Meta" vs "Meta Platforms Inc."

Examples:
- "Apple, Inc." -> "apple"
- "APPLE COMPUTER INC" -> "apple computer"
- "TechCorp S.r.l." -> "techcorp"
- "Deutsche Bank AG" -> "deutsche bank"

## Person Name Matching

Ranked by effectiveness for OSINT scenarios:

**Jaro-Winkler**: Best for name variations. Prioritizes prefix similarity. Use for: "Marco" vs "Marc", "Rossi" vs "Rossy"
**Levenshtein distance**: Good for typos and minor spelling variations. Use for: "Alessandro" vs "Alesandro"
**Token-based (Jaccard)**: Good for word-order variations. Use for: "John Smith" vs "Smith, John" vs "J. Smith"
**Phonetic (Soundex/Metaphone)**: Handles pronunciation-based variations. Use for: cross-language name matching

For common names (Smith, Rossi, Mueller), name matching alone is insufficient. Always combine with contextual signals.

## Confidence Scoring Framework

Each matching signal contributes a weighted score:

| Signal | Weight | Example |
|--------|--------|---------|
| Same email domain + similar name | +0.8 | john.smith@techcorp.com on Hunter.io + John Smith at TechCorp on LinkedIn |
| Same company mentioned in both profiles | +0.6 | "TechCorp" in GitHub org + "TechCorp CTO" in news article |
| Similar job title | +0.4 | "CTO" in one source, "Chief Technology Officer" in another |
| Same city/location | +0.3 | "Milan, Italy" in both sources |
| Username overlap | +0.2 | "jsmith" on GitHub, "jsmith" on Twitter |
| Same education institution | +0.2 | "MIT" in both sources |
| Co-authorship on same paper/patent | +0.7 | Both named as authors on the same publication |
| Profile photo match (if available) | +0.5 | Visual similarity (manual verification) |

**Decision thresholds:**
- Score >= 0.7: **Likely match** -- merge data, note confidence
- Score 0.4-0.7: **Possible match** -- flag for human review, keep separate until confirmed
- Score < 0.4: **No match** -- treat as distinct entities

## Blocking Strategy

For efficiency when dealing with many entities, reduce comparison space:

1. **Block by company**: Only compare people at the same (normalized) company
2. **Block by name prefix**: Only compare "John S*" with "John S*"
3. **Block by location**: Only compare people in the same city/region
4. **Block by role level**: Only compare C-level with C-level

Blocking reduces O(n^2) pairwise comparisons to manageable subsets.

## LLM-Assisted Validation

For ambiguous matches (score 0.4-0.7), use structured LLM reasoning:

Prompt pattern:
```
Given these two profiles from different sources, assess whether they are the same person:

Profile A (from {source_a}):
- Name: {name_a}
- Company: {company_a}
- Role: {role_a}
- Location: {location_a}
- Other signals: {signals_a}

Profile B (from {source_b}):
- Name: {name_b}
- Company: {company_b}
- Role: {role_b}
- Location: {location_b}
- Other signals: {signals_b}

Assess: same person, different person, or insufficient data to determine?
Provide reasoning and confidence (high/medium/low).
```

## Common Pitfalls

- **Username != identity**: "johndoe" on GitHub and Twitter may be different people. Always verify with contextual signals.
- **Company changes**: A person may have changed companies since one source was last updated. Check temporal consistency.
- **Name transliteration**: International names may appear differently across sources ("Alessandro" in Italian sources, "Alexander" in English sources).
- **Maiden/married names**: May cause false negatives. Cross-reference with other signals.
- **Company acquisitions**: "Clearbit" data might now appear under "HubSpot Breeze Intelligence". Track known acquisitions.

## Output Format

When documenting entity resolution results, use:

```json
{
  "entity_id": "person-001",
  "canonical_name": "Marco Rossi",
  "merged_from": [
    {"source": "github", "identifier": "mrossi", "confidence": 0.85},
    {"source": "semantic_scholar", "identifier": "M. Rossi", "confidence": 0.72},
    {"source": "web_search", "identifier": "Marco Rossi, CTO TechCorp", "confidence": 0.95}
  ],
  "resolution_method": "contextual_signals",
  "overall_confidence": "high",
  "flagged_for_review": false
}
```
