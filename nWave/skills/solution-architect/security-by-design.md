---
name: security-by-design
description: Security design principles, STRIDE threat modeling, OWASP Top 10 architectural mitigations, and secure patterns. Load when designing systems or reviewing architecture for security.
---

# Security by Design

## OWASP Security Design Principles

Apply these during design -- retrofitting security is 10-100x more expensive.

| # | Principle | Architect Action |
|---|-----------|-----------------|
| 1 | Security by Design | Include security requirements in architecture documents |
| 2 | Security by Default | Ship restrictive defaults; require explicit opt-in for relaxed settings |
| 3 | Defense in Depth | Layer controls: WAF + input validation + output encoding + parameterized queries |
| 4 | Fail Secure | Deny access on error; closed-by-default network policies |
| 5 | Least Privilege | Scoped service accounts; time-limited tokens; minimum permissions |
| 6 | Compartmentalize | Network segmentation; separate databases per trust level |
| 7 | Separation of Duties | Separate deployment approval from code authorship |
| 8 | Economy of Mechanism | Minimize attack surface; simple, auditable security code |
| 9 | Complete Mediation | Check authorization on every request; no cached auth decisions |
| 10 | Open Design | Use published, peer-reviewed algorithms; no security-through-obscurity |
| 11 | Least Common Mechanism | Separate admin and user interfaces |
| 12 | Psychological Acceptability | Make the secure path the easy path; minimize user friction |

## STRIDE Threat Modeling

Apply STRIDE to every component in a Data Flow Diagram (DFD). Four questions drive every session:
1. What are we working on? (system model)
2. What can go wrong? (threat identification)
3. What are we going to do about it? (mitigation)
4. Did we do a good enough job? (review)

### STRIDE Reference

| Threat | Violated Property | Architectural Mitigation |
|--------|-------------------|--------------------------|
| **Spoofing** | Authentication | MFA, mutual TLS, certificate pinning, OAuth2+PKCE |
| **Tampering** | Integrity | Input validation, HMAC, parameterized queries, immutable infra |
| **Repudiation** | Non-repudiation | Tamper-evident logging (append-only), digital signatures, SIEM |
| **Info Disclosure** | Confidentiality | Encryption at rest+transit, least privilege, generic error messages |
| **Denial of Service** | Availability | Rate limiting, circuit breakers, auto-scaling, query complexity limits |
| **Elevation of Privilege** | Authorization | Least privilege, RBAC/ABAC, signed tokens verified server-side |

### STRIDE per DFD Element

| DFD Element | Most Relevant Threats |
|-------------|----------------------|
| External Entity | Spoofing |
| Process | All six STRIDE threats |
| Data Store | Tampering, Info Disclosure, Repudiation, DoS |
| Data Flow | Tampering, Info Disclosure, DoS |
| Trust Boundary | Spoofing, Tampering, Elevation of Privilege |

### Risk Response Options

| Response | When | Example |
|----------|------|---------|
| Mitigate | Probable and impactful; controls feasible | Add MFA for spoofing on admin login |
| Eliminate | Remove feature/component entirely | Remove unused admin API endpoint |
| Transfer | Better managed by another party | Use managed IdP (Auth0, Cognito) |
| Accept | Low risk; mitigation cost exceeds impact | Accept DoS risk on internal status page |

## OWASP Top 10 -- Architectural Prevention

Focus on what the architect decides at design time, not implementation details.

### A01: Broken Access Control (61% of breaches)

- Deny by default -- no endpoint open unless explicitly granted
- Centralized authorization service (OPA, Casbin, Cedar), not scattered checks
- Resource-level ownership -- queries scoped to authenticated user
- ABAC over simple RBAC for complex multi-tenant systems
- CORS with explicit origin allowlists -- never wildcards with credentials

### A02/A05: Security Misconfiguration (rose to #2 in 2025)

- Infrastructure as Code with security scanning (tfsec, checkov) in CI/CD
- Hardened base images -- minimal containers with security baked in
- Configuration drift detection with automated alerting
- Environment parity -- same hardening across dev/staging/prod

### A03: Injection (SQL #2 in CWE Top 25 2025)

- Parameterized queries everywhere -- reject PRs with string concatenation in SQL
- Treat ALL database-sourced data as potentially tainted (second-order injection)
- Allowlisting for dynamic query elements (table names, sort columns)
- Template sandboxing -- user input as DATA, never as template source

### A04: Insecure Design (new in 2021)

- Mandate STRIDE analysis as gate for architecture reviews
- Abuse cases alongside every user story ("As an attacker, I want to...")
- State machines with explicit transitions for business logic
- Rate limiting built into architecture from day one

### A06/Supply Chain (expanded in 2025)

- SCA scanning on every commit (Snyk, Dependabot)
- SBOM generation as build artifact
- Private package registry; block direct public pulls in production builds
- Lock files committed with integrity hash verification

### A07: Authentication Failures

- Centralized IdP (Keycloak, Auth0, Cognito) -- no custom auth per service
- MFA required for sensitive data access and admin functions
- Progressive delays on failed attempts (exponential backoff, not permanent lockout)
- Session ID regeneration on every authentication state change

## Secure Architecture Patterns

### Zero Trust

Core: "Never trust, always verify" -- no implicit trust from network location.

| Component | Implementation |
|-----------|---------------|
| Identity verification | OAuth2/OIDC for users; mTLS for services |
| Transport security | mTLS everywhere; service mesh (Istio, Linkerd) |
| Micro-segmentation | Network policies limiting service-to-service |
| Continuous verification | Re-authenticate and re-authorize every request |
| Least privilege access | Scoped tokens; just-in-time access |

### Input Validation Pipeline

```
User Input
  -> Validation (allowlist, type, length, format)
    -> Business Logic (parameterized queries, ORM)
      -> Output Encoding (context-aware: HTML, JS, URL, CSS)
        -> Client
```

Key: input validation is complementary, not primary defense. Output encoding prevents XSS. Parameterized queries prevent SQLi. Validation adds defense in depth.

### Secrets Management

| Pattern | Implementation |
|---------|---------------|
| Centralized vault | HashiCorp Vault, AWS Secrets Manager, Azure Key Vault |
| Sidecar injection | Vault agent injects secrets into pods at runtime |
| Encrypted in repo | SOPS + KMS for GitOps workflows |
| Pre-commit scanning | gitleaks or TruffleHog blocks secrets before they reach git |

Rules: never in source code | never in container images | rotate automatically | separate per environment | audit all access.

### Required HTTP Security Headers

| Header | Value | Purpose |
|--------|-------|---------|
| Content-Security-Policy | Strict nonce-based | Prevent XSS |
| Strict-Transport-Security | `max-age=63072000; includeSubDomains; preload` | Force HTTPS |
| X-Content-Type-Options | `nosniff` | Prevent MIME sniffing |
| X-Frame-Options | `DENY` or `SAMEORIGIN` | Prevent clickjacking |
| Referrer-Policy | `strict-origin-when-cross-origin` | Control referrer |
| Permissions-Policy | Feature-specific | Limit browser APIs |

## Security Testing in CI/CD

| Type | Tests | Pipeline Stage | Tools |
|------|-------|---------------|-------|
| SAST | Source code vulnerabilities | Every commit/PR | Semgrep, CodeQL, SonarQube |
| SCA | Dependency CVEs | Build stage | Snyk, Dependabot, Trivy |
| DAST | Running application | Staging | OWASP ZAP, Burp Suite |
| Secrets | Leaked credentials | Pre-commit + CI | gitleaks, TruffleHog |

Strategy: SAST pre-commit (fast) -> SCA at build -> container scan -> DAST on staging -> block on critical/high findings.

## API Security Checklist (OWASP API Top 10)

| # | Threat | Architect Decision |
|---|--------|--------------------|
| API1 | BOLA (~40% of API attacks) | Object-level authorization in service layer, not just routes |
| API4 | Unrestricted resource consumption | Rate limiting per-object, not just per-endpoint |
| API5 | BFLA | Separate admin and user API surfaces |
| API6 | Sensitive business flow abuse | State machine enforcement, idempotency keys |
| API9 | Improper inventory management | API versioning with sunset policies; deprecate old versions |
| API10 | Unsafe API consumption | Never trust third-party API responses; validate and sanitize |

### GraphQL-Specific

- Disable introspection in production
- Set maximum query depth (10 levels) and complexity limits
- Limit batch size; exclude sensitive operations from batching
- Field-level authorization in resolvers

## Defensive Coding Patterns (Cross-Reference for Crafters)

| Risk | Vulnerable Pattern | Secure Alternative |
|------|-------------------|-------------------|
| SQL Injection | `f"SELECT * FROM users WHERE name = '{name}'"` | Parameterized: `cursor.execute("... WHERE name = %s", (name,))` |
| Deserialization | `pickle.loads(untrusted)` | `json.loads(untrusted)` or Pydantic schema validation |
| Command Injection | `os.system(f"cmd {input}")` | `subprocess.run(["cmd", input], shell=False)` |
| SSTI | `Template(user_input)` | `env.from_string(trusted).render(data=user_input)` |
| Mass Assignment | `User(**request.json())` | DTO with explicit fields, server-set for sensitive |
| TOCTOU Race | Read-check-write in separate steps | Atomic conditional update (`UPDATE ... WHERE condition`) |
| Prototype Pollution (JS) | `Object.assign(target, untrusted)` | `Map`, null-prototype objects, strict schema validation |
