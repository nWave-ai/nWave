---
name: nw-compliance-framework
description: GDPR LIA template, CCPA thresholds, ethical OSINT principles, data retention policies, and clear boundaries for what CAN vs SHOULD NOT be collected.
disable-model-invocation: true
---

# Compliance Framework

## Ethical OSINT Principles

These principles are non-negotiable:

1. **Public data only**: Collect data that is publicly accessible or obtained through legitimate API access. Never circumvent access controls, authentication, or paywalls.
2. **No social engineering**: Do not create fake profiles, impersonate individuals, or use deception.
3. **Proportionality**: Depth of investigation proportional to business purpose. Pre-meeting prep does not justify deep personal investigation.
4. **Transparency of methods**: Document sources consulted and methods used in the research log.
5. **Data subject dignity**: Do not collect embarrassing personal information even if publicly available.

## Collection Boundaries

### Permissible (collect freely)

- Publicly listed business role and company affiliation
- Published articles, papers, patents, conference talks
- Public social media posts (with caveat: public != no privacy expectation)
- Company registration data from official registries
- Published financial data (SEC filings, annual reports)
- Technology stack from website analysis
- Job postings from public career pages
- News articles and press releases
- Open source contributions (GitHub, GitLab public repos)

### Collect with caution (document justification)

- Business email addresses (legitimate interest assessment needed)
- Business phone numbers
- Salary data from public filings (executive compensation in SEC proxy)
- Historical employment data from non-public aggregators

### Do not collect

- Private social media content (even if technically accessible via privacy gaps)
- Health information, political opinions, religious beliefs (GDPR Art. 9 special categories)
- Personal financial information (salary for non-executives, credit data)
- Family member information
- Location tracking or movement patterns
- Private communications (even if leaked/hacked)
- Home address (unless part of public company filing)
- Biometric data (photographs used for identification purposes)

## GDPR Compliance (EU Data Subjects)

### When GDPR Applies

GDPR applies to processing personal data of EU residents regardless of where the processing organization is based. Flag any data subject located in the EU.

### Lawful Basis: Legitimate Interest (Art. 6(1)(f))

Best fit for sales preparation. Requires a documented Legitimate Interest Assessment (LIA).

### LIA Template

Include this in every dossier involving EU data subjects:

```
LEGITIMATE INTEREST ASSESSMENT
Purpose: Sales meeting preparation -- understanding business context of {subject name}
Legitimate Interest: Personalizing business approach, demonstrating credibility,
  avoiding wasted meetings, building productive business relationships
Necessity Test: Required to prepare effectively. No less intrusive alternative
  provides the same business context.
Balancing Test:
  - Data is publicly available (company websites, registries, published articles)
  - No special categories (Art. 9) collected
  - Individual impact minimal (professional context only, not private life)
  - Reasonable expectation: business professionals expect public professional
    presence to be viewed for business purposes
Safeguards:
  - Data retention: {6|12} months, then delete or re-assess
  - Right to erasure: mechanism available on request
  - No automated decision-making (Art. 22) -- intelligence for human review only
  - Data stored locally, not shared with third parties
Conclusion: Legitimate interest satisfied for this collection scope
```

### Key GDPR Obligations

| Obligation | Requirement | Implementation |
|-----------|------------|----------------|
| Purpose limitation | Data for sales prep only, not repurposed | Document purpose in dossier metadata |
| Data minimization | Collect only what is needed | Follow collection boundaries above |
| Storage limitation | Retention period defined | Set `data_retention_recommendation` in dossier |
| Right to erasure (Art. 17) | Delete all data on request | Dossier files can be deleted from output directory |
| Right to access (Art. 15) | Export all data on request | Dossier JSON serves as the complete record |
| Transparency (Art. 14) | Notify when collecting from third parties | Most challenging obligation -- see note below |

### Art. 14 Notification Challenge

Art. 14 requires notifying data subjects when collecting data from third-party sources (within 1 month). For small-scale sales preparation, the "disproportionate effort" exemption (Art. 14(5)(b)) may apply. Document this reasoning in the LIA. Seek legal opinion for larger-scale operations.

## CCPA Compliance (California Residents)

### When CCPA Applies

CCPA applies if the organization meets any threshold:
- Annual gross revenue >= $26.625M (2025 threshold), OR
- Buy/sell/share personal information of 100K+ California residents, OR
- Derive 50%+ revenue from selling/sharing personal data

For small-scale sales preparation, CCPA thresholds are unlikely to be met. Monitor if operations scale.

### If CCPA Applies

- Provide notice at collection (types and purposes)
- Support right to know, right to delete, right to opt-out
- No discrimination against consumers exercising rights
- Fines: $2,500 per violation (unintentional), $7,500 (intentional)

## Data Retention Policy

| Dossier Type | Recommended Retention | Rationale |
|-------------|----------------------|-----------|
| Person dossier | 6 months | Professional data changes frequently (job changes, roles) |
| Company dossier | 12 months | Company data more stable but financials update quarterly |
| Relationship map | 12 months | Relationship networks evolve slowly |
| Meeting brief | 3 months | Time-bound to specific meeting context |

After retention period: delete dossier files or trigger re-enrichment for ongoing relationships.

## Compliance Note Template (for dossier)

Include in every dossier:

```
## Compliance Note

- EU Data Subject: {yes/no}
- GDPR LIA: {documented above / not applicable}
- Data collected from: {list of source types -- public registries, news, APIs}
- Special categories (Art. 9): None collected
- Retention recommendation: {6/12 months from generation date}
- Collection date: {ISO-8601}
- Right to erasure: Delete files in {output_directory}
```
