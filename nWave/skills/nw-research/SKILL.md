---
name: nw-research
description: "Gathers knowledge from web and files, cross-references across multiple sources, and produces cited research documents. Use when investigating technologies, patterns, or decisions that need evidence backing."
user-invocable: true
argument-hint: '[topic] - Optional: --research_depth=[overview|detailed|comprehensive|deep-dive] --skill-for=[agent-name]'
---

# NW-RESEARCH: Evidence-Driven Knowledge Research

**Wave**: CROSS_WAVE
**Agent**: Nova (nw-researcher)
**Command**: `*research`

## Overview

Systematic evidence-based research with source verification. Cross-wave support providing research-backed insights for any nWave phase using trusted academic|official|industry sources.

Optional `--skill-for={agent-name}` distills research into a practitioner-focused skill file for a specific agent.

## Orchestration: Trusted Source Config

At orchestration time, before invoking the researcher subagent:

1. **Read Config** — Read `.nwave/trusted-source-domains.yaml` from the project root. Gate: file read attempted.
2. **Seed If Missing** — If file missing, write it from the defaults in `## Default Trusted Sources` below, then notify the user: "Seeded `.nwave/trusted-source-domains.yaml` with defaults (7 categories, 42 trusted domains, 5 excluded). Edit the YAML directly to customize." Gate: file exists.
3. **Embed Config** — Embed the YAML content inline in the researcher subagent Task prompt so the agent receives trusted source config via prompt context. Gate: YAML present in Task prompt.

## Agent Invocation

@nw-researcher

Execute \*research on {topic} [--skill-for={agent-name}].

**Configuration:**
- research_depth: detailed # overview/detailed/comprehensive/deep-dive
- source_preferences: ["academic", "official", "technical_docs"]
- output_directory: docs/research/
- skill_for: {agent-name} # Optional: distilled skill for specified agent
- skill_output_directory: ~/.claude/nWave/skills/{agent-name}/

## Output Management

The researcher MUST create the output file in the FIRST 5 turns with a document skeleton (title, sections, placeholders). All subsequent findings are written DIRECTLY to this file as they are gathered — never held only in context.

If the agent is interrupted or runs out of turns, the output file contains all work done so far. This is the researcher's equivalent of the crafter's "commit early, commit often."

1. **Skeleton** — By turn ~5: Create output file with title, sections, and placeholders. Gate: output file exists.
2. **First Findings** — By turn ~10: Write initial gathered findings to file. Gate: file has substantive content.
3. **Ongoing Writes** — By turn ~25: Write all gathered findings so far. Gate: no findings held only in context.
4. **Synthesize** — By turn ~35: Stop gathering, begin synthesizing. Gate: synthesis section started.
5. **Polish** — Turn ~45+: Polish and finalize only. Gate: research document complete.

## Success Criteria

**Research:**
- [ ] All sources from trusted source domains from prompt context
- [ ] Cross-reference performed (3+ sources per major claim ideal, 2 acceptable, 1 authoritative minimum)
- [ ] Research file created in docs/research/
- [ ] Citation coverage > 95%
- [ ] Average source reputation >= 0.80

**Distillation (if --skill-for specified):**
- [ ] Skill file created in ~/.claude/nWave/skills/{agent-name}/
- [ ] 100% essential concepts preserved
- [ ] Self-contained with no external references
- [ ] Token budget respected (<5000 tokens per skill)

## Next Wave

**Handoff To**: Invoking workflow
**Deliverables**: Research document + optional skill file

## Examples

### Example 1: Standalone research
```
/nw-research "event sourcing patterns" --research_depth=detailed
```
Nova researches event sourcing from trusted sources, cross-references 3+ sources per claim, produces comprehensive research document.

### Example 2: Research with agent skill
```
/nw-research "mutation testing methodologies" --skill-for=software-crafter
```

## Expected Outputs

```
docs/research/{category}/{topic}-comprehensive-research.md
~/.claude/nWave/skills/{agent}/{topic}-methodology.md    (if --skill-for)
```

## Default Trusted Sources

The following YAML is the default content for `.nwave/trusted-source-domains.yaml`. It is seeded automatically when the file does not exist.

```yaml
# Trusted Source Domains for Evidence-Driven Research
# Used by knowledge-researcher agent to validate source credibility

# High-reputation academic and research sources
academic:
  description: "Peer-reviewed academic and research institutions"
  domains:
    - "*.edu"
    - "*.ac.uk"
    - "scholar.google.com"
    - "arxiv.org"
    - "pubmed.ncbi.nlm.nih.gov"
    - "researchgate.net"
    - "ieee.org"
    - "acm.org"
    - "springer.com"
    - "sciencedirect.com"
    - "jstor.org"
    - "nature.com"
    - "science.org"
  reputation: high
  verification_requirements:
    - peer_review_preferred
    - citation_tracking
    - author_credentials

# Official standards bodies and government sources
official:
  description: "Government, standards organizations, and official documentation"
  domains:
    - "*.gov"
    - "*.gov.uk"
    - "w3.org"
    - "ietf.org"
    - "iso.org"
    - "nist.gov"
    - "docs.microsoft.com"
    - "docs.oracle.com"
    - "docs.python.org"
    - "docs.oracle.com/javase"
    - "kubernetes.io/docs"
    - "docker.com/docs"
  reputation: high
  verification_requirements:
    - official_publication
    - version_tracking
    - standards_compliance

# Industry leaders and recognized experts
industry_leaders:
  description: "Established technology companies and recognized industry experts"
  domains:
    - "github.com"
    - "stackoverflow.com"
    - "martinfowler.com"
    - "refactoring.guru"
    - "enterpriseintegrationpatterns.com"
    - "microservices.io"
    - "12factor.net"
    - "reactivemanifesto.org"
    - "agilemanifesto.org"
    - "thoughtworks.com/insights"
    - "infoq.com"
  reputation: medium-high
  verification_requirements:
    - cross_reference_required
    - author_expertise_validation
    - community_consensus

# Technical documentation and established platforms
technical_documentation:
  description: "Official technical documentation and established platforms"
  domains:
    - "developer.mozilla.org"
    - "developers.google.com"
    - "aws.amazon.com/documentation"
    - "cloud.google.com/docs"
    - "learn.microsoft.com"
    - "devdocs.io"
    - "readthedocs.org"
  reputation: high
  verification_requirements:
    - version_accuracy
    - official_source_confirmation

# Open source foundations and communities
open_source:
  description: "Recognized open source foundations and communities"
  domains:
    - "apache.org"
    - "eclipse.org"
    - "cncf.io"
    - "opensource.org"
    - "fsf.org"
    - "linuxfoundation.org"
  reputation: high
  verification_requirements:
    - community_validation
    - project_maturity_check

# Medium-trust sources requiring additional verification
medium_trust:
  description: "Quality sources requiring cross-referencing"
  domains:
    - "medium.com"
    - "dev.to"
    - "hashnode.com"
  reputation: medium
  verification_requirements:
    - author_verification_required
    - minimum_3_source_cross_reference
    - fact_checking_mandatory

# Excluded sources - unreliable or promotional
excluded:
  description: "Sources excluded due to low quality control or bias"
  domains:
    - "*.blogspot.com"
    - "wordpress.com"
    - "tumblr.com"
    - "pastebin.com"
    - "quora.com"
  reason: "Unverified sources, potential bias, low quality control, no editorial oversight"
  action: "Reject and log warning"

# Source validation rules
validation_rules:
  minimum_sources_per_claim: 3
  cross_reference_required: true

  reputation_scoring:
    high: 1.0
    medium-high: 0.8
    medium: 0.6
    low: 0.0

  confidence_thresholds:
    high_confidence:
      min_sources: 3
      min_avg_reputation: 0.8
    medium_confidence:
      min_sources: 2
      min_avg_reputation: 0.6
    low_confidence:
      min_sources: 1
      min_avg_reputation: 0.4

  required_metadata:
    - source_url
    - domain
    - access_date
    - reputation_score
    - verification_status

# Research quality guidelines
quality_guidelines:
  evidence_standards:
    - "Direct quotes or data from reputable sources"
    - "Proper attribution and citation"
    - "Version information for technical documentation"
    - "Publication date or last update date"
    - "Author credentials when available"

  bias_detection:
    - "Check for commercial interests or sponsorship"
    - "Identify potential conflicts of interest"
    - "Verify with independent sources"
    - "Note any disclaimers or limitations"

  conflicting_information:
    - "Document all conflicting sources"
    - "Evaluate source reliability for each claim"
    - "Present both sides with evidence"
    - "Note which sources are more authoritative"
```
