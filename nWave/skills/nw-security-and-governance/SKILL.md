---
name: nw-security-and-governance
description: "Database security, data governance, and compliance frameworks (GDPR, CCPA, HIPAA). Load when implementing encryption, access control, injection prevention, data lineage, or auditing compliance requirements."
user-invocable: false
disable-model-invocation: true
---

# Security and Governance

## Defense-in-Depth Security Model

Layered security, each layer provides independent protection:
1. **Encryption at rest** (TDE) — protects against physical media theft
2. **Encryption in transit** (TLS/SSL) — protects against network interception
3. **Access control** (RBAC/ABAC) — enforces least privilege
4. **SQL injection prevention** — protects against application-layer attacks
5. **Audit logging** — accountability and forensic capability

## Encryption at Rest (TDE)

Encrypts DB files on disk without application changes. Encrypts data pages before writing, decrypts on read into memory. AES 128/256-bit symmetric encryption. Transparent to applications.

### Key Hierarchy (SQL Server)
1. Service Master Key (Windows DPAPI) -> 2. Database Master Key -> 3. Certificate -> 4. Database Encryption Key (DEK)

### Implementation
```sql
-- SQL Server TDE (key hierarchy: Service Master Key -> DB Master Key -> Certificate -> DEK)
CREATE DATABASE ENCRYPTION KEY WITH ALGORITHM = AES_256
    ENCRYPTION BY SERVER CERTIFICATE TDE_Cert;
ALTER DATABASE [YourDB] SET ENCRYPTION ON;
-- PostgreSQL: pgcrypto for column-level, full TDE in v17+ | Oracle: ALTER SYSTEM SET ENCRYPTION KEY
```

### Best Practices
- Back up certificates/keys immediately — loss means unrecoverable data
- Store backups in separate secure location | Implement key rotation policy
- Use customer-managed keys (BYOK) for regulatory compliance
- Monitor performance impact (typically 3-5% overhead)
- TDE does not protect data in memory — use column-level encryption for highly sensitive fields

## Encryption in Transit (TLS)

### Configuration Checklist
- [ ] TLS 1.2+ enforced (disable 1.0/1.1)
- [ ] Valid certificates from trusted CA (not self-signed in prod)
- [ ] Certificate rotation policy established
- [ ] Client cert auth for server-to-server connections
- [ ] Connection string enforces SSL (`sslmode=require` in PostgreSQL)

## Access Control

### RBAC (Role-Based)
Assign permissions to roles, roles to users. Standard in all major DBs.

```sql
-- PostgreSQL RBAC: create roles with specific grants, assign to users
CREATE ROLE app_readonly; GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;
CREATE ROLE app_readwrite; GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_readwrite;
GRANT app_readonly TO reporting_user; GRANT app_readwrite TO application_user;
```

### ABAC (Attribute-Based)
Access decisions based on attributes of user, resource, environment. More flexible than RBAC for complex scenarios (multi-tenant, data classification).

### Least Privilege
- Application accounts: DML only (SELECT/INSERT/UPDATE/DELETE)
- Migration accounts: DDL + DML, time-limited
- Admin accounts: full access, MFA required, audit logged
- Reporting accounts: SELECT only on specific schemas/views

## SQL Injection Prevention (OWASP)

### Parameterized Queries (Primary Defense)

```python
# VULNERABLE - string concatenation (SQL injection risk)
query = f"SELECT * FROM users WHERE name = '{user_input}'"

# SAFE - parameterized (all languages: Python %s, Java ?, C# @param, Node.js $1)
cursor.execute("SELECT * FROM users WHERE id = %s AND status = %s", (user_id, 'active'))
```

### Additional Defenses (OWASP)
Input validation: whitelist allowed chars/formats | Stored procedures: reduce direct SQL exposure | Least privilege: no DDL for app accounts | WAF rules | Never expose DB error messages to end users

## Data Governance

### Data Lineage
Track data from source through transformations to consumption:
- **Technical lineage**: Column-level mapping through ETL/ELT pipelines
- **Business lineage**: Business meaning and ownership
- **Tools**: Apache Atlas, OpenLineage, Marquez, dbt lineage, AWS Glue, Azure Purview

Purpose: Regulatory compliance (GDPR Article 30) | Impact analysis (downstream schema change effects) | Root cause analysis (bad data origin) | Audit trails

### Data Quality Dimensions

| Dimension | Definition | Example Check |
|-----------|-----------|---------------|
| Accuracy | Correctly represents real-world entities | Email format validation |
| Completeness | Required fields populated | NOT NULL checks, completeness % |
| Consistency | Same data across systems agrees | Cross-system reconciliation |
| Timeliness | Current and available when needed | Freshness SLAs |
| Uniqueness | No unintended duplicates | Duplicate detection on business keys |
| Validity | Conforms to defined rules/formats | Range checks, enum validation |

### Master Data Management (MDM)
Establish single source of truth for core entities (customer, product, location) | Define golden record resolution rules | Implement data stewardship roles | Use MDM platform or reference data services

## Compliance Frameworks

### GDPR (EU)
- **Right to erasure** (Art. 17): Hard-delete capability including backups/replicas
- **Data portability** (Art. 20): Export in machine-readable format (JSON, CSV)
- **Consent management**: Track per processing purpose with timestamps
- **Data minimization**: Collect/retain only necessary personal data
- **Privacy by design**: Pseudonymization, encryption, access controls from initial design
- **Breach notification**: 72-hour requirement, implement detection/alerting

### CCPA (California)
Right to know (disclose collected data) | Right to delete | Right to opt-out of data sale | Non-discrimination regardless of privacy choices

### HIPAA (Health Data)
PHI encryption at rest and in transit | Role-based access with minimum necessary standard | Audit all PHI access | Business associate agreements for third-party processors

### Implementation Checklist
- [ ] Data classification schema (public, internal, confidential, restricted)
- [ ] Retention policies per classification
- [ ] Deletion procedures (including backups, replicas, caches)
- [ ] Consent tracking mechanism
- [ ] Audit logging for sensitive data access
- [ ] Data processing records (GDPR Art. 30)
- [ ] Breach response procedure documented and tested
- [ ] Privacy impact assessment for new processing activities

## Backup and Recovery

### 3-2-1 Rule
3 copies of data | 2 different storage types | 1 copy offsite

### Backup Types
- **Full**: Complete DB copy, baseline for recovery
- **Incremental**: Changed blocks since last backup, fast/small, recovery requires chain
- **Differential**: Changes since last full, faster recovery than incremental chain
- **Transaction log**: Enables point-in-time recovery (PITR)

### Recovery Validation
Test recovery regularly (monthly minimum) | Document RTO and RPO | Encrypt backup files | Store encryption keys separately from backups
