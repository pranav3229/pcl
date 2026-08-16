# Security Policy

## 1. Security in PCL

The **Physical Capability Language (PCL)** involves cryptographic signatures (Ed25519, ECDSA P-256), JSON Canonicalization (RFC 8785 JCS), and deterministic constraint verification.

Security vulnerabilities in canonicalization, signature parsing, or constraint evaluation algorithms could lead to false verification decisions or spoofed outcome attestations.

---

## 2. Reporting a Vulnerability

If you discover a potential security vulnerability in the PCL specification, schemas, or reference implementation:

- **DO NOT** create a public GitHub issue.
- Please report vulnerabilities privately to enable coordinated disclosure.

> **Director Notice / TODO:**
> The project director will designate the official private security contact email (e.g., `security@pcl.dev` or GitHub Security Advisories) prior to public release. In the interim, please contact the repository maintainers directly.

---

## 3. Scope of Security Concerns

We actively investigate:
- Cryptographic bypasses or canonicalization collisions in `sdk/python/pcl/canonical.py`.
- Signature forgery or public key confusion attacks in `sdk/python/pcl/crypto.py`.
- Fail-closed bypasses in constraint matching or evidence verification (`sdk/python/pcl/verifier.py`).
- Injection vulnerabilities in dot-path parameter resolution.
