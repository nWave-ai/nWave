---
name: infrastructure-and-observability
description: Infrastructure as Code patterns (Terraform, Kubernetes), observability design (SLOs, metrics, alerting, dashboards), and pipeline security stages. Load when designing infrastructure, observability, or security scanning.
---

# Infrastructure as Code and Observability

## Terraform Patterns

### Module Structure
- `main.tf` -- Resource definitions
- `variables.tf` -- Input variable declarations
- `outputs.tf` -- Output value declarations
- `versions.tf` -- Provider and terraform version constraints
- `README.md` -- Module documentation

### State Management
- Remote backend: S3/GCS/Azure Blob with state locking
- State locking: DynamoDB/Cloud Storage/Azure Blob lease
- Workspace strategy: one workspace per environment (dev/staging/prod)

### Security
- Never commit secrets -- use secret managers
- Encrypt state at rest
- Use OIDC for CI/CD authentication
- Least privilege IAM roles

### IaC Principles (Kief Morris)
- Reproducibility -- same input, same output
- Idempotency -- safe to run multiple times
- Immutability -- replace, do not modify
- Version control -- track all changes

### IaC Patterns
- **Stack pattern**: Complete infrastructure as single unit
- **Library pattern**: Reusable infrastructure modules
- **Pipeline pattern**: Infrastructure changes through CI/CD

## Kubernetes Patterns

### Core Concepts
Pods, Deployments, Services, Ingress, ConfigMaps, Secrets, PersistentVolumes, RBAC, NetworkPolicies, PodSecurityPolicies, Operators, Custom Resources, Controllers.

### Production Patterns
- Multi-tenancy with namespaces
- Resource quotas and limits
- Pod disruption budgets
- Horizontal and vertical autoscaling

### Deployment Template
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .name }}
  labels:
    app: {{ .name }}
    version: {{ .version }}
spec:
  replicas: {{ .replicas }}
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 0
  template:
    spec:
      containers:
      - name: {{ .name }}
        image: {{ .image }}:{{ .tag }}
        resources:
          requests:
            memory: {{ .memoryRequest }}
            cpu: {{ .cpuRequest }}
          limits:
            memory: {{ .memoryLimit }}
            cpu: {{ .cpuLimit }}
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

### HPA Template
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ .name }}
  minReplicas: {{ .minReplicas }}
  maxReplicas: {{ .maxReplicas }}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Observability Design

### SLO Design
**Availability SLO**: `successful_requests / total_requests * 100`
- 99.9% = 8.76 hours downtime/year
- 99.95% = 4.38 hours downtime/year
- 99.99% = 52.6 minutes downtime/year
- Error budget = 100% - SLO target

**Latency SLO**: `requests_under_threshold / total_requests * 100`
- 99% of requests < 200ms
- 99.9% of requests < 1000ms

### Metrics Methods

**RED Method** (request-driven services):
- Rate: requests per second
- Errors: error rate (percentage)
- Duration: latency distribution (p50, p90, p99)

**USE Method** (resources -- CPU, memory, disk):
- Utilization: percentage used
- Saturation: queue depth, waiting requests
- Errors: error counts for the resource

**Four Golden Signals** (Google SRE):
- Latency, Traffic, Errors, Saturation

### SLO-Based Alerting
- Fast burn: >14.4x burn rate for 1 hour -> page
- Slow burn: >6x burn rate for 6 hours -> ticket
- Budget nearly exhausted: >50% consumed -> warning

Alert structure: alertname, severity, service, SLO name, current value, threshold, runbook URL, dashboard URL.

### Dashboard Design (per service)
- Request rate (RPS)
- Error rate (%)
- Latency distribution (p50, p90, p99)
- SLO status and error budget
- Resource utilization (CPU, memory)
- Dependency health

### Three Pillars of Observability (Charity Majors)
- **Logs**: Event records with structured context. Use structured logging with correlation IDs.
- **Metrics**: Numeric measurements over time. Use RED/USE/Golden Signals.
- **Traces**: Request flow across services. Use distributed tracing with sampling.

Principles: high cardinality is essential, debug in production, understand unknown unknowns.

## Pipeline Security

### Security Stages

**Pre-commit**: Secrets scanning (pre-commit hooks), linting. Tools: pre-commit, gitleaks, detect-secrets.

**Commit stage**: SAST, dependency scanning (SCA), license compliance, secrets scanning. Tools: Semgrep/CodeQL/Bandit/SonarQube (SAST), Dependabot/Snyk/Trivy (SCA), Gitleaks/TruffleHog (secrets).

**Build stage**: Container image scanning, SBOM generation, image signing. Tools: Trivy/Grype/Clair (scanning), Syft/CycloneDX (SBOM), Cosign/Notary (signing).

**Pre-production**: DAST, API security testing, infrastructure security scanning. Tools: OWASP ZAP/Nuclei (DAST), Checkov/tfsec/Terrascan (infrastructure).

**Runtime**: Runtime security monitoring, network policy enforcement, admission control. Tools: Falco/Sysdig (runtime), OPA Gatekeeper/Kyverno (admission).

### Secrets Management
Principles: never commit secrets, use short-lived credentials, rotate regularly, audit access.
- External secrets: fetch from vault at runtime (HashiCorp Vault, AWS Secrets Manager, GCP Secret Manager)
- SOPS: encrypt secrets in git with GPG/KMS (for GitOps workflows)

### Supply Chain Security
- SBOM: Software Bill of Materials in SPDX or CycloneDX format, generated during build
- SLSA levels: L1 (documented build), L2 (version control + build service), L3 (isolated builds + signed provenance), L4 (two-party review + hermetic builds)
