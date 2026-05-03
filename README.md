# IMM-CI Self-Assessment Tool

[![Tests](https://github.com/sunilgentyala/imm-ci-framework/actions/workflows/tests.yml/badge.svg)](https://github.com/sunilgentyala/imm-ci-framework/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![IEEE Paper](https://img.shields.io/badge/IEEE-SmartNets%202026-blue)](https://edas.info/showPaper.php?m=1571252869)
[![Cite](https://img.shields.io/badge/cite-CITATION.cff-orange)](CITATION.cff)

Companion artifact to the IEEE SmartNets 2026 paper:

> **"The Metamorphosis of Access: Strategic Imperatives for Identity 3.0 and Zero Trust Integration in Critical Infrastructure"**
> Sunil Gentyala, Floriano Caprio — HCLTech, Dallas TX
> *SmartNets 2026 — CyberSec CIIA | IEEE Xplore (forthcoming)*

---

## What Is the IMM-CI?

The **Identity Maturity Model for Critical Infrastructure (IMM-CI)** is a five-level framework that evaluates an organization's IAM capability, Zero Trust posture, and post-quantum cryptography readiness as a single unified progression — not three separate workstreams.

Most IAM maturity models treat these as independent tracks. The IMM-CI integrates them because they are genuinely interdependent: your PQC migration choices are constrained by your current authentication infrastructure; your Zero Trust posture determines how much blast radius a compromised identity can create. A Level 3 IAM posture combined with Level 1 PQC readiness is a specific, identifiable risk — and the model makes that asymmetry visible.

| Level | Stage | IAM | Zero Trust | PQC |
|-------|-------|-----|------------|-----|
| 1 | Foundational | Password auth, basic RBAC, manual JML | Perimeter-based | Classical only (RSA, ECC) |
| 2 | Structured | MFA enforced, LDAP/AD, partial ABAC | Network segmentation, some ZT policies | Crypto inventory documented |
| 3 | Defined | FIDO2/passkeys, SCIM, ITDR deployed | Identity as control plane, CAEP/RISC | Hybrid classical-PQC in test |
| 4 | Managed | SPIFFE/SPIRE, DIDs piloted, SSF integrated | Continuous evaluation, behavioral analytics | ML-KEM/ML-DSA in production |
| 5 | Optimized | Full SSI, verifiable credentials, AI ITDR | Full ZTA, cryptographic attestation | Cryptographic agility achieved |

The Level 2→3 transition is where most industrial operators stall. This tool is designed specifically to diagnose why.

---

## Quick Start

```bash
git clone https://github.com/sunilgentyala/imm-ci-framework.git
cd imm-ci-framework
pip install -r requirements.txt

# Run against the included Lakeshore MWA sample (Level 2 baseline)
python imm_ci_assessor.py --config config/sample_org.yaml

# Run interactively against your own environment
python imm_ci_assessor.py --interactive

# Export results to JSON (for GRC integration or audit trail)
python imm_ci_assessor.py --config config/sample_org.yaml --json-out results.json
```

---

## Sample Output

Running the tool against the included `config/sample_org.yaml` (a Level 2 municipal water utility profile):

```
======================================================================
  IMM-CI ASSESSMENT REPORT
  Lakeshore Metropolitan Water Authority (Pilot Baseline)  |  2026-05-03
======================================================================

  EXECUTIVE SUMMARY
  Lakeshore Metropolitan Water Authority assessed at IMM-CI Level 2 (Structured).
  IAM: L2 | Zero Trust: L2 | PQC Readiness: L2.
  The organization shows the Level 2->3 stall pattern identified in the IMM-CI model.
  Vendor coordination, downtime window planning, and FIDO2 HMI compatibility are likely blockers.

  [IAM Capabilities]  Score: 28.6/100  ->  Level 2
    Gaps:
      - Missing capability: SCIM provisioning active
      - Missing capability: FIDO2/passkeys deployed
      - Missing capability: ITDR deployed
    Next Steps:
      -> Implement: FIDO2/passkeys deployed (impact weight: 20)
      -> Implement: SCIM provisioning active (impact weight: 15)
      -> Implement: ITDR deployed (impact weight: 15)

  [Zero Trust Posture]  Score: 25.0/100  ->  Level 2
    Next Steps:
      -> Implement: Identity is the control plane (impact weight: 20)
      -> Implement: CAEP/RISC session signals active (impact weight: 15)

  [PQC Readiness]  Score: 18.2/100  ->  Level 2
    Next Steps:
      -> Implement: Cryptographic agility achieved (impact weight: 25)
      -> Implement: ML-KEM / ML-DSA in production (impact weight: 25)

  COMPOSITE LEVEL: 2/5
  *** L2->L3 STALL PATTERN DETECTED -- see Section XII of IMM-CI paper ***

  TOP PRIORITY ACTIONS
  1. Implement: FIDO2/passkeys deployed (impact weight: 20)
  2. Implement: SCIM provisioning active (impact weight: 15)
  3. Implement: Identity is the control plane (impact weight: 20)
  4. Implement: CAEP/RISC session signals active (impact weight: 15)
  5. Implement: Cryptographic agility achieved (impact weight: 25)
  6. Implement: ML-KEM / ML-DSA in production (impact weight: 25)
======================================================================
```

---

## Configuration Reference

Copy `config/sample_org.yaml` and edit it to match your environment. Each key maps to a specific IMM-CI control:

```yaml
organization: "Your Organization Name"

iam:
  password_only: false        # Any system uses password-only auth?
  mfa_enforced: true          # MFA enforced for ALL users?
  ldap_ad_integration: true   # LDAP/AD integrated?
  partial_abac: false         # Attribute-based access control (partial)?
  fido2_deployed: false       # FIDO2/passkeys deployed?
  scim_provisioning: false    # SCIM provisioning active?
  itdr_deployed: false        # ITDR platform deployed?
  spiffe_spire: false         # SPIFFE/SPIRE for workload identity?
  dids_piloted: false         # Decentralized Identifiers piloted?
  full_ssi: false             # Full SSI / verifiable credentials?
  autonomous_jml: false       # Autonomous JML lifecycle?

zero_trust:
  perimeter_only: false       # Still purely perimeter-based?
  network_segmentation: true  # Network segmentation in place?
  some_zt_policies: true      # Some Zero Trust policies enforced?
  identity_control_plane: false
  caep_risc_active: false
  continuous_evaluation: false
  behavioral_analytics: false
  full_zta: false
  crypto_attestation_all: false

pqc:
  classical_only: false       # Classical only, no plan at all?
  crypto_inventory: true      # Cryptographic inventory documented?
  migration_plan: false       # PQC migration plan exists?
  hybrid_pqc_test: false      # Hybrid PQC in test environments?
  mlkem_mldsa_production: false
  crypto_agility_achieved: false
```

### Scoring Notes

- **Composite level** uses the weakest-link principle: `min(IAM level, ZT level, PQC level)`. A Level 4 IAM posture with Level 1 PQC readiness gives a composite of Level 1 — the model makes that gap visible rather than averaging it away.
- **Scores are normalized** per dimension against the maximum possible positive weight for that rubric. This means Level 2 capability combinations consistently score in the 20–35 range and Level 3 combinations in the 35–70 range across all three dimensions.
- **Stall detection** flags the L2→L3 pattern: IAM at Level 2, ZT at Level 2–3, PQC at Level 1–2. This is the most common failure mode for industrial operators documented in the paper.

---

## Grounding Standards

The IMM-CI rubric maps directly to published standards:

| Control Area | Standard |
|---|---|
| Identity Assurance Levels | NIST SP 800-63-4 (2025) |
| Identity Management Vocabulary | ISO/IEC 24760-1:2024 |
| Entity Authentication Assurance | ISO/IEC 29115:2013 |
| Passwordless Authentication | FIDO2/WebAuthn; NIST SP 800-63-4 AAL2 |
| Provisioning | RFC 7643 (SCIM Core Schema) |
| Machine Identity | SPIFFE/SPIRE (CNCF, 2024) |
| Continuous Session Evaluation | OpenID CAEP 1.0; OpenID SSF 1.0 |
| Key Encapsulation (PQC) | FIPS 203 — ML-KEM (August 2024) |
| Digital Signatures (PQC) | FIPS 204 — ML-DSA (August 2024) |
| Zero Trust Architecture | NIST SP 800-207 |
| Verifiable Credentials | W3C VC Data Model v2.0 (2024) |

---

## Empirical Validation

The tool's level definitions were validated against a structured 18-month pilot at a municipal water authority (14 treatment facilities, Siemens SIMATIC S7-300/400 PLCs, Wonderware SCADA). The pilot confirmed Level 2 at baseline and Level 3 post-implementation, with the following measured outcomes:

| Metric | Baseline (L2) | Post-Pilot (L3) |
|--------|--------------|-----------------|
| Deprovisioning latency (mean) | 5.2 days | 2.8 hours (−93%) |
| FIDO2 on privileged accounts | 0% | 100% |
| Machine identity w/ defined expiry | 34% | 91% |
| Machine identity w/ auto-rotation | 11% | 68% |
| Password-only on OT-access systems | Present | Eliminated |
| Open NERC CIP audit findings | 2 | 0 |
| ITDR high-severity events (90 days) | None detected | 12 confirmed |

Full methodology in the companion paper (citation below).

---

## Running the Tests

```bash
pip install pytest pyyaml
pytest tests/ -v
```

Expected output:

```
27 passed in 0.03s
```

Test coverage includes: dimension scoring, composite level (weakest-link), stall detection,
Lakeshore baseline profile (Level 2), Lakeshore post-pilot profile (Level 3), JSON output,
pilot delta (all three dimensions improve, composite advances).

---

## How to Cite

If you use this tool or the IMM-CI framework in your research, please cite the companion paper:

### BibTeX

```bibtex
@inproceedings{gentyala2026metamorphosis,
  author    = {Gentyala, Sunil and Caprio, Floriano},
  title     = {The Metamorphosis of Access: Strategic Imperatives for Identity 3.0
               and Zero Trust Integration in Critical Infrastructure},
  booktitle = {Proceedings of SmartNets 2026 -- International Conference on Smart
               Applications, Communications and Networking (CyberSec CIIA Track)},
  year      = {2026},
  publisher = {IEEE},
  note      = {EDAS Paper ID: 1571252869. To appear in IEEE Xplore.}
}
```

### IEEE Format

S. Gentyala and F. Caprio, "The Metamorphosis of Access: Strategic Imperatives for Identity 3.0 and Zero Trust Integration in Critical Infrastructure," in *Proc. SmartNets 2026 -- Int. Conf. Smart Applications, Communications and Networking (CyberSec CIIA)*, IEEE, 2026.

### Software Citation

To cite this tool specifically, use the `CITATION.cff` file in this repository. GitHub will surface a "Cite this repository" button automatically.

---

## Authors

**Sunil Gentyala** — IEEE Senior Member
Cybersecurity and AI Security, HCLTech, Dallas, TX, USA
sunil.gentyala@ieee.org | [IEEE Profile](https://www.ieee.org)

**Floriano Caprio**
HCLTech (HCL America Inc.), Dallas, TX, USA
floriano.caprio@hcltech.com

---

## License

MIT — see [LICENSE](LICENSE).

**Software (this repository):** MIT license — unrestricted research and practitioner use.

**Associated paper:** Copyright transferred to IEEE (signed 03-05-2026) for the 2026 International Conference on Smart Applications, Communications and Networking (SmartNets). Per IEEE Author Online Use policy:

- The **accepted manuscript** (not the final IEEE-typeset version) may be posted on personal or institutional servers with a prominently displayed IEEE copyright notice and full citation linking to the IEEE Xplore abstract.
- The **final published PDF** from IEEE Xplore may not be redistributed or posted anywhere.
- After publication, any preprint must be replaced with a full citation and DOI link to the IEEE Xplore record.

This repository contains only the companion **software artifact** — not the manuscript. The code is independently MIT-licensed.

---

## Related Work

- Mudusu & Gentyala 2026 — Zero-trust AI pipelines: DOI 10.70589/JRTCSE.2026.14.2.2
- Gentyala 2026 — AI-SBOM: DOI 10.14738/tmlai.1401.19884
- Gentyala 2026 — Frontiers: DOI 10.3389/fcomp.2026.1735919
