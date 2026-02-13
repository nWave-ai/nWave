---
name: authoritative-sources
description: Domain-specific authoritative source databases, search strategies by topic category, and source freshness rules
---

# Authoritative Sources

## Domain Authority Database

Use this database to identify the most authoritative sources for a given research domain. These supplement the general reputation tiers in the `source-verification` skill with domain-specific authorities.

### Software Architecture
| Source | Authority | Notes |
|--------|-----------|-------|
| martinfowler.com | Primary authority | Patterns, refactoring, enterprise architecture |
| c2.com/wiki | Historical reference | Original wiki; pattern language origins |
| microservices.io | Domain-specific authority | Chris Richardson's microservices patterns |
| architecturenotes.co | Curated reference | Architecture decision records and trade-off analysis |
| infoq.com | Industry reporting | Conference talks and practitioner reports |
| thoughtworks.com/radar | Trend tracking | Technology Radar for adoption lifecycle |

### Cloud Platforms
| Source | Authority | Notes |
|--------|-----------|-------|
| docs.aws.amazon.com | Official documentation | AWS services, well-architected framework |
| cloud.google.com/docs | Official documentation | GCP services and best practices |
| learn.microsoft.com | Official documentation | Azure, .NET, and Microsoft ecosystem |
| kubernetes.io/docs | Official documentation | Container orchestration reference |
| docs.docker.com | Official documentation | Container runtime reference |

### Security
| Source | Authority | Notes |
|--------|-----------|-------|
| owasp.org | Standards body | Web application security standards and top-10 lists |
| nist.gov | Government authority | Security frameworks (NIST CSF, SP 800 series) |
| cve.mitre.org | Vulnerability database | CVE identifiers and vulnerability details |
| nvd.nist.gov | Vulnerability database | National Vulnerability Database with scoring |
| csrc.nist.gov | Cryptography standards | FIPS, cryptographic module validation |
| cisa.gov | Government advisory | Security advisories and alerts |

### Standards Bodies
| Source | Authority | Notes |
|--------|-----------|-------|
| ietf.org / datatracker.ietf.org | Protocol standards | RFCs for networking, HTTP, TLS, DNS |
| w3.org | Web standards | HTML, CSS, accessibility (WCAG), web APIs |
| iso.org | International standards | Quality, security, process frameworks |
| ecma-international.org | Language standards | ECMAScript (JavaScript) specification |
| unicode.org | Character standards | Unicode standard and encoding |

### Programming Languages and Frameworks
| Source | Authority | Notes |
|--------|-----------|-------|
| docs.python.org | Official documentation | Python language, stdlib, PEPs |
| go.dev/doc | Official documentation | Go language, standard library, blog |
| typescriptlang.org | Official documentation | TypeScript language, handbook |
| rust-lang.org/learn | Official documentation | Rust language, book, reference |
| developer.mozilla.org (MDN) | Canonical web reference | JavaScript, HTML, CSS, Web APIs |
| docs.oracle.com/javase | Official documentation | Java language specification, API docs |

### Data and Databases
| Source | Authority | Notes |
|--------|-----------|-------|
| postgresql.org/docs | Official documentation | PostgreSQL reference and guides |
| dev.mysql.com/doc | Official documentation | MySQL reference manual |
| redis.io/docs | Official documentation | Redis commands and data types |
| mongodb.com/docs | Official documentation | MongoDB reference and guides |
| cassandra.apache.org/doc | Official documentation | Apache Cassandra documentation |

### DevOps and SRE
| Source | Authority | Notes |
|--------|-----------|-------|
| sre.google | Industry authority | Google SRE books and practices |
| 12factor.net | Methodology reference | Twelve-factor app methodology |
| dora.dev | Research authority | DevOps Research and Assessment (DORA metrics) |
| openpolicyagent.org | Policy-as-code | OPA documentation and patterns |

## Domain-Specific Search Strategies

### Architecture Topics
1. Start with canonical authors: search `{topic} site:martinfowler.com` or `site:microservices.io`
2. Check conference talks: search `{topic} QCon OR StrangeLoop OR GOTO conference`
3. Look for books and papers: search `{topic} book OR paper architecture`
4. Check Technology Radar for adoption status: search `{topic} site:thoughtworks.com/radar`
5. Search local project docs: `Grep` for the topic in `docs/research/` and `nWave/skills/`

### Security Topics
1. Check vulnerability databases first: search `{topic} site:cve.mitre.org` or `site:nvd.nist.gov`
2. Check advisory sources: search `{topic} site:cisa.gov` or `site:owasp.org`
3. Search NIST for frameworks: search `{topic} site:nist.gov`
4. Check vendor advisories if product-specific
5. Recency is critical -- prioritize results from the last 6 months

### Framework and Library Topics
1. Start with official documentation (see domain database above)
2. Check release notes and changelogs for version-specific information
3. Search migration guides: `{framework} migration guide {version}`
4. Check GitHub issues and discussions for known problems and workarounds
5. Search Stack Overflow for practitioner experience: `{topic} site:stackoverflow.com`

### Methodology and Process Topics
1. Search for the original author or publication
2. Look for case studies: `{methodology} case study OR experience report`
3. Check for critiques and alternatives: `{methodology} criticism OR alternative OR comparison`
4. Search academic sources: `{topic} site:arxiv.org` or Google Scholar
5. Look for practitioner adaptations vs. original definitions

## Source Freshness Rules

Source recency requirements vary by domain. Apply these rules when evaluating whether a source is current enough to cite.

| Category | Maximum Age | Rationale |
|----------|------------|-----------|
| Security vulnerabilities | 6 months | Threat landscape evolves rapidly; older advisories may be patched |
| Framework versions | 1 year | APIs and best practices change with major releases |
| Cloud service documentation | 1 year | Cloud providers deprecate and launch services frequently |
| API references | 1 year | Breaking changes common in active projects |
| Architecture patterns | Evergreen | Core patterns (CQRS, event sourcing) are stable concepts |
| Methodology references | Evergreen | Foundational works (DDD, TDD, Agile Manifesto) remain relevant |
| Language specifications | Evergreen per version | Spec for a given version is permanent; check which version is current |
| Research papers | 3 years | Academic findings remain valid longer but check for follow-up work |
| Industry trend reports | 1 year | Technology Radar, State of DevOps -- only cite current edition |

### Handling Outdated Sources

When a source exceeds its freshness threshold:
1. Check if a newer version of the same source exists
2. If the core claim is about a stable concept (architecture, methodology), cite with a note: "[Published {year}; concept remains current]"
3. If the claim is time-sensitive (security, framework version), find a current source or document the age limitation in Knowledge Gaps
4. Never cite outdated security advisories as current threat intelligence
