# IMM-CI Methodology Reference

**Identity Maturity Model for Critical Infrastructure (IMM-CI)**
Gentyala & Caprio, SmartNets 2026 CyberSec CIIA

This document describes the scoring methodology, rubric design, and
assessment protocol implemented in `imm_ci_assessor.py`. It is a technical
reference for researchers extending or adapting the framework — not a
reproduction of the paper.

---

## Scoring Architecture

### Three Independent Dimensions

The IMM-CI scores an organization across three dimensions simultaneously:

| Dimension | What It Measures | Key Standards |
|-----------|-----------------|---------------|
| IAM Capabilities | Authentication strength, provisioning automation, machine identity governance, lifecycle management | NIST SP 800-63-4, ISO/IEC 24760, FIDO2/WebAuthn, RFC 7643 (SCIM), SPIFFE |
| Zero Trust Posture | Trust evaluation model, session continuity, behavioral analytics, cryptographic attestation | NIST SP 800-207, OpenID CAEP 1.0, OpenID SSF 1.0 |
| PQC Readiness | Cryptographic inventory, migration planning, algorithm agility, post-quantum deployment | FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), NIST SP 800-207 |

### Normalized Per-Dimension Scoring

Each dimension is scored independently using a weighted rubric. Raw scores
are normalized against the maximum possible positive weight for that rubric:

```
normalized_score = max(0, min(100, raw_weight_sum / max_positive_weight * 100))
```

This means capability combinations map consistently to score ranges regardless
of how many controls are in each rubric.

**Calibration:** Rubric weights are calibrated so that the capability set
described at each IMM-CI level consistently scores within the expected band:

| Level | Band | Rationale |
|-------|------|-----------|
| 1 | 0 – 14 | No structured controls; negative-weight penalties apply |
| 2 | 15 – 34 | Foundational controls (MFA, directory, segmentation, inventory) |
| 3 | 35 – 69 | Phishing-resistant auth, automated provisioning, active detection |
| 4 | 70 – 84 | Workload identity, behavioral analytics, PQC in production |
| 5 | 85 – 100 | Full SSI, complete ZTA, cryptographic agility achieved |

Per-dimension thresholds differ slightly because each rubric has different
maximum weight totals (IAM: 140, ZT: 120, PQC: 110).

### Weakest-Link Composite

```
composite_level = min(IAM_level, ZT_level, PQC_level)
```

This implements the weakest-link principle from NIST SP 800-207 Section 2:
a Zero Trust posture is only as strong as its weakest assurance dimension.
Averaging the three levels would mask asymmetric gaps that represent
specific, actionable risks. A Level 4 IAM posture with Level 1 PQC
readiness is not a "Level 2.5 organization" — it is a Level 1 PQC risk
that requires a specific remediation path.

---

## IAM Capabilities Rubric

| Control Key | Weight | Rationale |
|-------------|--------|-----------|
| `password_only` | −30 | Presence of password-only auth on any system is a direct Level 1 indicator; penalizes score regardless of other controls |
| `mfa_enforced` | +20 | Core Level 2 gate; enforced for all users, not optional |
| `ldap_ad_integration` | +10 | Centralized directory is the prerequisite for provisioning automation |
| `partial_abac` | +10 | Attribute-based access indicates movement beyond flat RBAC |
| `fido2_deployed` | +20 | Primary Level 3 gate; phishing-resistant, hardware-bound auth |
| `scim_provisioning` | +15 | Automated deprovisioning closes the access removal latency gap |
| `itdr_deployed` | +15 | Active threat detection on identity layer |
| `spiffe_spire` | +15 | Machine identity lifecycle management at Level 4 scale |
| `dids_piloted` | +10 | Decentralized identity piloting indicates Level 4 progression |
| `full_ssi` | +15 | Full Self-Sovereign Identity is the Level 5 IAM endpoint |
| `autonomous_jml` | +10 | AI-driven lifecycle management at Level 5 |

**Maximum positive total: 140**

---

## Zero Trust Posture Rubric

| Control Key | Weight | Rationale |
|-------------|--------|-----------|
| `perimeter_only` | −20 | Implicit internal trust directly contradicts ZT principles |
| `network_segmentation` | +20 | Minimum ZT network control; Level 2 gate |
| `some_zt_policies` | +10 | Partial ZT policy enforcement indicates Level 2 maturity |
| `identity_control_plane` | +20 | Identity-as-perimeter is the core Level 3 ZT posture |
| `caep_risc_active` | +15 | Real-time session signals; closes post-authentication trust gap |
| `continuous_evaluation` | +15 | Per-request/per-transaction evaluation; Level 4 capability |
| `behavioral_analytics` | +15 | ML-based anomaly detection on identity events |
| `full_zta` | +15 | Complete ZTA deployment per NIST SP 800-207 |
| `crypto_attestation_all` | +10 | Cryptographic attestation on all entities; Level 5 endpoint |

**Maximum positive total: 120**

---

## PQC Readiness Rubric

| Control Key | Weight | Rationale |
|-------------|--------|-----------|
| `classical_only` | −10 | No awareness of PQC risk; no inventory in place |
| `crypto_inventory` | +20 | Prerequisite for all migration planning; Level 2 gate |
| `migration_plan` | +20 | Documented plan is the Level 3 PQC gate |
| `hybrid_pqc_test` | +20 | Hybrid classical-PQC testing validates migration path |
| `mlkem_mldsa_production` | +25 | FIPS 203/204 in production; Level 4 capability |
| `crypto_agility_achieved` | +25 | Algorithm-agnostic IAM infrastructure; Level 5 endpoint |

**Maximum positive total: 110**

---

## Level 2 to Level 3 Stall Detection

The assessor flags the L2->L3 stall pattern when:

```python
iam.level == 2 AND zt.level <= 3 AND pqc.level <= 2
```

This condition captures the most common failure mode observed in industrial
operator IAM programs: authentication controls at MFA/LDAP with no
phishing-resistant auth, Zero Trust posture not yet using identity as the
control plane, and PQC inventory documented but no migration plan.

The stall is not a scoring artifact — it reflects a structural constraint
in industrial environments where FIDO2 deployment is blocked by HMI
compatibility, SCIM integration requires LDAP proxy architecture, and
ITDR is deferred due to perceived OT telemetry requirements.

---

## Four-Step Assessment Protocol

These four steps translate the IMM-CI rubric into executable field work.
All four can be completed by an internal identity team without external
consultants.

### Step 1: Authentication Mechanism Survey

Enumerate every system requiring authentication. Record actual mechanism:
- `password_only`: any privileged system with password-only auth
- `mfa_enforced`: is MFA enforced for 100% of users, or are exceptions present?
- `fido2_deployed`: are hardware-bound phishing-resistant authenticators deployed?

**Key threshold:** Any system with privileged OT access using password-only
authentication places the organization at Level 1 for IAM, regardless of
what other controls exist.

### Step 2: Provisioning Latency Measurement

Starting from a known identity lifecycle event (contractor offboarding,
employee termination), measure elapsed time until access is confirmed
removed from all in-scope systems.

**Key threshold:** If deprovisioning latency exceeds 24 hours for any
system with OT access, provisioning automation is the highest-priority
remediation — ahead of authentication upgrades.

**Baseline measurement method:**
1. Select 3-5 recent offboarding events from HR records
2. Pull access logs from each in-scope system
3. Compute time delta: termination event -> last confirmed access removal
4. Record mean and worst-case

### Step 3: Machine Identity Inventory

Enumerate all non-human credentials: service accounts, API keys, TLS
certificates, SSH keys, and OT device certificates.

For each credential, record three attributes:
- **Defined expiry**: Does it have an expiration date?
- **Automated rotation**: Is rotation handled by tooling, or manual?
- **Anomalous-use detection**: Does anything alert if this credential
  authenticates to an unusual system?

**Reference ratio:** Human-to-machine identity ratio in enterprise
environments runs 1:10 to 1:45 (CyberArk 2024). Manual management at
this scale is operationally untenable.

### Step 4: Cryptographic Inventory

Document every algorithm in use across IAM infrastructure:
- TLS cipher suites on identity providers
- Token signing algorithms (RS256, ES256, etc.)
- Certificate signature algorithms
- WebAuthn attestation certificate algorithms
- Any legacy endpoints using SHA-1 or RSA < 2048

**Output format:** A table of `[system, algorithm, key_length, expiry,
PQC_migration_required]` that enables scope and cost estimation for
ML-KEM and ML-DSA integration.

---

## Extending the Framework

### Adding a New Sector Profile

Create a YAML file in `config/` following the schema in `config/sample_org.yaml`.
All keys must be present; missing keys default to `False` in the assessor.

### Adapting Rubric Weights

Edit the `IAM_RUBRIC`, `ZT_RUBRIC`, and `PQC_RUBRIC` dictionaries in
`imm_ci_assessor.py`. After changing weights, re-run the test suite to
verify that named profiles still score at expected levels:

```bash
pytest tests/ -v -k "TestNamedProfiles"
```

### Adding New Controls

1. Add the control to the appropriate rubric with a weight and label.
2. Add it to all existing YAML configs (with an appropriate default).
3. Add a test case in `TestDimensionScoring` or `TestNamedProfiles`.
4. Document the rationale and grounding standard in this file.

### Integration with GRC Tooling

The `--json-out` flag produces a structured JSON report. The schema is:

```json
{
  "org_name": "string",
  "assessment_date": "YYYY-MM-DD",
  "composite_level": 1-5,
  "stall_warning": true/false,
  "executive_summary": "string",
  "iam_score": { "level": 1-5, "raw_score": 0-100, "gaps": [], "next_steps": [] },
  "zt_score":  { "level": 1-5, "raw_score": 0-100, "gaps": [], "next_steps": [] },
  "pqc_score": { "level": 1-5, "raw_score": 0-100, "gaps": [], "next_steps": [] },
  "priority_actions": ["string", ...]
}
```

---

## Validation

The framework was empirically validated through an 18-month pilot at a
municipal water utility (Lakeshore Metropolitan Water Authority). See
`results/benchmark_results.json` for cross-sector benchmark outputs, and
`tests/lakeshore_baseline_result.json` for the pilot baseline assessment.

Measured outcomes confirming Level 3 criteria:
- Deprovisioning latency: 5.2 days -> 2.8 hours (-93%)
- FIDO2 on privileged accounts: 0% -> 100%
- Machine identity with defined expiry: 34% -> 91%
- Password-only on OT-access systems: eliminated
- Open compliance findings: 2 -> 0

Full methodology: see companion paper (SmartNets 2026, IEEE).
