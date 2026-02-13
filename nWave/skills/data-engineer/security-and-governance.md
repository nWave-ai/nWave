---
name: security-and-governance
description: Database security (encryption, access control, injection prevention), data governance (lineage, quality, MDM), and compliance frameworks (GDPR, CCPA, HIPAA)
---

# Security and Governance

## Defense-in-Depth Security Model

Security is layered. Each layer provides independent protection:

1. **Encryption at rest** (TDE) — protects against physical media theft
2. **Encryption in transit** (TLS/SSL) — protects against network interception
3. **Access control** (RBAC/ABAC) — enforces least privilege
4. **SQL injection prevention** — protects against application-layer attacks
5. **Audit logging** — provides accountability and forensic capability

## Encryption at Rest (TDE)

Transparent Data Encryption encrypts database files on disk without application changes.

### How TDE Works
- Encrypts data pages before writing to disk
- Decrypts data pages when reading into memory
- Uses symmetric encryption (AES 128/256-bit)
- Transparent to applications — no code changes

### Encryption Key Hierarchy (SQL Server)
1. Service Master Key (protected by Windows DPAPI)
2. Database Master Key (protected by Service Master Key)
3. Certificate (protected by Database Master Key)
4. Database Encryption Key (DEK, protected by certificate)

### Implementation
```sql
-- SQL Server TDE
CREATE MASTER KEY ENCRYPTION BY PASSWORD = '<strong_password>';
CREATE CERTIFICATE TDE_Cert WITH SUBJECT = 'TDE Certificate';
CREATE DATABASE ENCRYPTION KEY WITH ALGORITHM = AES_256
    ENCRYPTION BY SERVER CERTIFICATE TDE_Cert;
ALTER DATABASE [YourDB] SET ENCRYPTION ON;

-- PostgreSQL (pgcrypto for column-level, full TDE in v17+)
-- Oracle TDE
ALTER SYSTEM SET ENCRYPTION KEY IDENTIFIED BY "<keystore_password>";
ALTER TABLESPACE users ENCRYPTION ONLINE USING 'AES256';
```

### Best Practices
- Back up certificates and keys immediately after creation — loss means unrecoverable data
- Store backups in separate secure location
- Implement key rotation policy
- Use customer-managed keys (BYOK) for regulatory compliance
- Monitor performance impact (typically 3-5% overhead)
- TDE does not protect data in memory — use column-level encryption for highly sensitive fields

## Encryption in Transit (TLS)

### Configuration Checklist
- [ ] TLS 1.2+ enforced (disable TLS 1.0/1.1)
- [ ] Valid certificates from trusted CA (not self-signed in production)
- [ ] Certificate rotation policy established
- [ ] Client certificate authentication for server-to-server connections
- [ ] Connection string enforces SSL (`sslmode=require` in PostgreSQL)

## Access Control

### RBAC (Role-Based Access Control)
Assign permissions to roles, assign roles to users. Standard in all major databases.

```sql
-- PostgreSQL RBAC example
CREATE ROLE app_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;

CREATE ROLE app_readwrite;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_readwrite;

-- Assign to users
GRANT app_readonly TO reporting_user;
GRANT app_readwrite TO application_user;
```

### ABAC (Attribute-Based Access Control)
Access decisions based on attributes of user, resource, and environment. More flexible than RBAC for complex scenarios (multi-tenant, data classification).

### Least Privilege Principle
- Application accounts: Only DML (SELECT, INSERT, UPDATE, DELETE)
- Migration accounts: DDL + DML, time-limited
- Admin accounts: Full access, MFA required, audit logged
- Reporting accounts: SELECT only on specific schemas/views

## SQL Injection Prevention (OWASP)

### Parameterized Queries (Primary Defense)

```python
# Python (psycopg2)
cursor.execute("SELECT * FROM users WHERE id = %s AND status = %s", (user_id, 'active'))

# Java (PreparedStatement)
# PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?");
# ps.setInt(1, userId);

# C# (SqlCommand with parameters)
# cmd.Parameters.AddWithValue("@id", userId);

# Node.js (pg library)
# client.query('SELECT * FROM users WHERE id = $1', [userId])
```

### Additional Defenses (OWASP Recommendations)
- Input validation: Whitelist allowed characters and formats
- Stored procedures: Encapsulate queries, reduce direct SQL exposure
- Least privilege: Application DB accounts should not have DDL permissions
- WAF rules: Web application firewall for additional filtering
- Error handling: Never expose database error messages to end users

### Detection Patterns
Look for string concatenation in SQL construction:
```python
# VULNERABLE - string concatenation
query = f"SELECT * FROM users WHERE name = '{user_input}'"

# SAFE - parameterized
query = "SELECT * FROM users WHERE name = %s"
cursor.execute(query, (user_input,))
```

## Data Governance

### Data Lineage
Track data from source through transformations to consumption:
- **Technical lineage**: Column-level mapping through ETL/ELT pipelines
- **Business lineage**: Business meaning and ownership of data elements
- **Tools**: Apache Atlas, OpenLineage, Marquez, dbt lineage, cloud-native (AWS Glue, Azure Purview)

Purpose:
- Regulatory compliance (GDPR Article 30: records of processing activities)
- Impact analysis (what downstream systems are affected by a schema change?)
- Root cause analysis (where did bad data originate?)
- Audit trails (who accessed what data, when?)

### Data Quality Dimensions
Measure and monitor these dimensions:

| Dimension | Definition | Example Check |
|-----------|-----------|---------------|
| Accuracy | Data correctly represents real-world entities | Email format validation |
| Completeness | Required fields are populated | NOT NULL checks, completeness % |
| Consistency | Same data across systems agrees | Cross-system reconciliation |
| Timeliness | Data is current and available when needed | Freshness SLAs |
| Uniqueness | No unintended duplicates | Duplicate detection on business keys |
| Validity | Data conforms to defined rules and formats | Range checks, enum validation |

### Master Data Management (MDM)
- Establish single source of truth for core entities (customer, product, location)
- Define golden record resolution rules for conflicting data
- Implement data stewardship roles and processes
- Use MDM platform or implement reference data services

## Compliance Frameworks

### GDPR (EU General Data Protection Regulation)
Key requirements for database design:
- **Right to erasure** (Article 17): Implement hard-delete capability for personal data, including backups and replicas
- **Data portability** (Article 20): Export user data in machine-readable format (JSON, CSV)
- **Consent management**: Track consent per data processing purpose with timestamps
- **Data minimization**: Collect and retain only necessary personal data
- **Privacy by design**: Pseudonymization, encryption, access controls from initial design
- **Breach notification**: 72-hour notification requirement — implement detection and alerting

### CCPA (California Consumer Privacy Act)
- **Right to know**: Disclose what personal data is collected
- **Right to delete**: Delete personal data on request
- **Right to opt-out**: Opt-out of data sale
- **Non-discrimination**: Equal service regardless of privacy choices

### HIPAA (Health Data)
- **PHI encryption**: Encrypt Protected Health Information at rest and in transit
- **Access controls**: Role-based access with minimum necessary standard
- **Audit trails**: Log all access to PHI
- **Business associate agreements**: Required for third-party data processors

### Implementation Checklist
- [ ] Data classification schema defined (public, internal, confidential, restricted)
- [ ] Retention policies per data classification
- [ ] Deletion procedures (including backups, replicas, caches)
- [ ] Consent tracking mechanism
- [ ] Audit logging for sensitive data access
- [ ] Data processing records (GDPR Article 30)
- [ ] Breach response procedure documented and tested
- [ ] Privacy impact assessment for new data processing activities

## Backup and Recovery

### 3-2-1 Rule
- 3 copies of data
- 2 different storage types
- 1 copy offsite

### Backup Types
- **Full**: Complete database copy. Baseline for recovery
- **Incremental**: Changed blocks since last backup. Fast, small. Recovery requires chain
- **Differential**: Changes since last full backup. Faster recovery than incremental chain
- **Transaction log**: Enables point-in-time recovery (PITR)

### Recovery Validation
- Test recovery regularly (monthly minimum)
- Document RTO (Recovery Time Objective) and RPO (Recovery Point Objective)
- Encrypt backup files
- Store backup encryption keys separately from backups
