---
name: nw-authoritative-sources
description: "Curates authoritative sources by domain with search strategies and freshness rules. Use when verifying citations, researching technology choices, or validating source credibility."
user-invocable: false
disable-model-invocation: true
---

# Authoritative Sources

## Domain Authority Database

Supplements general reputation tiers in `source-verification` with domain-specific authorities.

### Software Architecture
| Source | Authority | Notes |
|--------|-----------|-------|
| martinfowler.com | Primary | Patterns, refactoring, enterprise architecture |
| c2.com/wiki | Historical | Original wiki; pattern language origins |
| microservices.io | Domain-specific | Chris Richardson's microservices patterns |
| architecturenotes.co | Curated | ADRs and trade-off analysis |
| infoq.com | Industry reporting | Conference talks, practitioner reports |
| thoughtworks.com/radar | Trend tracking | Technology Radar adoption lifecycle |

### Cloud Platforms
| Source | Authority | Notes |
|--------|-----------|-------|
| docs.aws.amazon.com | Official | AWS, well-architected framework |
| cloud.google.com/docs | Official | GCP services and practices |
| learn.microsoft.com | Official | Azure, .NET, Microsoft ecosystem |
| kubernetes.io/docs | Official | Container orchestration |
| docs.docker.com | Official | Container runtime |

### Security
| Source | Authority | Notes |
|--------|-----------|-------|
| owasp.org | Standards body | Web app security, top-10 |
| nist.gov | Government | NIST CSF, SP 800 series |
| cve.mitre.org | Vuln database | CVE identifiers |
| nvd.nist.gov | Vuln database | NVD with scoring |
| csrc.nist.gov | Crypto standards | FIPS, module validation |
| cisa.gov | Government advisory | Security advisories |

### Standards Bodies
| Source | Authority | Notes |
|--------|-----------|-------|
| ietf.org / datatracker.ietf.org | Protocol standards | RFCs: networking, HTTP, TLS, DNS |
| w3.org | Web standards | HTML, CSS, WCAG, web APIs |
| iso.org | International | Quality, security, process frameworks |
| ecma-international.org | Language standards | ECMAScript spec |
| unicode.org | Character standards | Unicode encoding |

### Programming Languages and Frameworks
| Source | Authority | Notes |
|--------|-----------|-------|
| docs.python.org | Official | Python, stdlib, PEPs |
| go.dev/doc | Official | Go language, stdlib |
| typescriptlang.org | Official | TypeScript handbook |
| rust-lang.org/learn | Official | Rust book, reference |
| developer.mozilla.org (MDN) | Canonical web ref | JS, HTML, CSS, Web APIs |
| docs.oracle.com/javase | Official | Java spec, API docs |

### Data and Databases
| Source | Authority | Notes |
|--------|-----------|-------|
| postgresql.org/docs | Official | PostgreSQL |
| dev.mysql.com/doc | Official | MySQL |
| redis.io/docs | Official | Redis |
| mongodb.com/docs | Official | MongoDB |
| cassandra.apache.org/doc | Official | Cassandra |

### DevOps and SRE
| Source | Authority | Notes |
|--------|-----------|-------|
| sre.google | Industry | Google SRE books |
| 12factor.net | Methodology | Twelve-factor app |
| dora.dev | Research | DORA metrics |
| openpolicyagent.org | Policy-as-code | OPA docs |

## Domain-Specific Search Strategies

### Architecture Topics
1. Canonical authors: `{topic} site:martinfowler.com` or `site:microservices.io`
2. Conference talks: `{topic} QCon OR StrangeLoop OR GOTO conference`
3. Books/papers: `{topic} book OR paper architecture`
4. Adoption status: `{topic} site:thoughtworks.com/radar`
5. Local docs: Grep in `docs/research/` and `nWave/skills/`

### Security Topics
1. Vuln databases: `{topic} site:cve.mitre.org` or `site:nvd.nist.gov`
2. Advisories: `{topic} site:cisa.gov` or `site:owasp.org`
3. NIST frameworks: `{topic} site:nist.gov`
4. Vendor advisories if product-specific
5. Prioritize last 6 months

### Framework and Library Topics
1. Official docs (see database above)
2. Release notes/changelogs for version-specific info
3. Migration guides: `{framework} migration guide {version}`
4. GitHub issues/discussions for known problems
5. Stack Overflow: `{topic} site:stackoverflow.com`

### Methodology and Process Topics
1. Original author/publication
2. Case studies: `{methodology} case study OR experience report`
3. Critiques: `{methodology} criticism OR alternative OR comparison`
4. Academic: `{topic} site:arxiv.org` or Google Scholar
5. Practitioner adaptations vs original definitions

## Source Freshness Rules

| Category | Max Age | Rationale |
|----------|---------|-----------|
| Security vulnerabilities | 6 months | Rapid threat evolution |
| Framework versions | 1 year | API/practice changes |
| Cloud service docs | 1 year | Frequent deprecation/launch |
| API references | 1 year | Breaking changes common |
| Architecture patterns | Evergreen | Core patterns stable |
| Methodology references | Evergreen | Foundational works stable |
| Language specs | Evergreen per version | Per-version permanent |
| Research papers | 3 years | Check for follow-up work |
| Industry trend reports | 1 year | Cite current edition only |

### Handling Outdated Sources
1. Check if newer version exists
2. Stable concept: cite with "[Published {year}; concept remains current]"
3. Time-sensitive: find current source or document age limitation in Knowledge Gaps
4. Never cite outdated security advisories as current threat intelligence
