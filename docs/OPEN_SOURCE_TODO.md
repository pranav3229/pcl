# Open-Source Governance & Legal Checklist
**Action Items for Project Director & Engineering Prior to Public Release**

---

This document outlines the governance, legal, and operational decisions required before publishing PCL as an open-source standard.

---

## PART I: DIRECTOR DECISIONS (Requires Project Director Authorization)

### 1. Legal & Licensing
- [ ] **License Selection:**
  - *Recommendation:* Apache 2.0 (standard for open protocols with explicit patent grant) or MIT.
  - *Action:* Formally approve license choice.
- [ ] **Copyright Ownership:**
  - *Options:* `Copyright (c) 2026 PCL Standard Authors` or organizational entity.
- [ ] **Trademark / Project Name:**
  - Confirm usage of "Physical Capability Language" and "PCL" trademark rights.

### 2. Community & Contribution Policy
- [ ] **Contributor Agreement Model:**
  - *Options:* Developer Certificate of Origin (DCO / `git commit -s`) vs. Contributor License Agreement (CLA).
  - *Recommendation:* DCO (low barrier for open-source participation).
- [ ] **Security Contact / Vulnerability Reporting:**
  - Designate the private security disclosure destination (e.g. `security@pcl.dev` or GitHub Security Advisories).

### 3. Protocol Evolution & Governance
- [ ] **Specification Change Policy:**
  - Approve RFC process for standard revisions.
- [ ] **Domain Vocabulary Working Groups:**
  - Define governance structure for registering standard domain vocabularies (e.g., logistics, manufacturing, healthcare).

---

## PART II: ENGINEERING ACTIONS (Completed / In Progress)

- [x] **Normative Specification Formalization:** `spec/SPEC.md` and `spec/MATCHING.md` authored.
- [x] **JSON Schema Draft 2020-12 Definitions:** `spec/schemas/*.json` validated.
- [x] **Portable Conformance Test Suite:** `spec/conformance/` populated.
- [x] **Developer Quickstart & Architecture Documentation:** `docs/QUICKSTART.md`, `docs/ARCHITECTURE.md`.
- [x] **Clean-Room Implementation Guide:** `docs/CLEAN_ROOM_IMPLEMENTATION.md`.
- [x] **GitHub Issue Templates:** Setup bug, specification ambiguity, and conformance failure templates.
- [x] **Release Packaging & Versioning Policy:** `docs/VERSIONING.md`, `CHANGELOG.md`, `docs/releases/0.1.0-alpha.md`.
- [x] **Security Disclosure Guide:** `SECURITY.md` created (with Director contact placeholder).
- [x] **Contribution Guidelines:** `CONTRIBUTING.md` authored.
- [x] **Repository Hygiene Audit:** Verified no local paths, credentials, or private keys exist.
