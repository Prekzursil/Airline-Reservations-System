# Curated SAST ruleset (Gate 4)

Pinned tool: **opengrep 1.22.0** (CI) — locally interchangeable with **semgrep CE**
(opengrep is a fork of semgrep and consumes the same rule syntax).

## Why an in-repo ruleset instead of `--config auto`

`--config auto` / `p/*` registry packs are fetched from the network at scan time and
change underneath you, which makes the gate **non-deterministic**. The lean model
requires a fixed, reviewable ruleset committed to the repo, so the gate produces the
same result every run, offline, with no registry login.

## Contents

A **curated subset** distilled from the relevant upstream packs (`p/c`, `p/python`,
`p/javascript`, `p/r2c-security-audit`) — the high-signal security rules that apply to
this codebase (a C++ reservation-system core + a React/JS GUI + Python quality/security
helper scripts):

- `cpp-security.yaml` — C/C++ command-injection / unbounded-copy / dangerous-function /
  insecure-temp-file patterns.
- `python-security.yaml` — Python injection / unsafe-deserialization / unsafe-subprocess /
  weak-crypto / TLS-verify-off patterns.
- `javascript-security.yaml` — JS XSS / `eval` / unsafe DOM sink / child_process /
  insecure-randomness patterns.
- `general-security.yaml` — language-agnostic patterns (private keys / cloud keys in code).

## Running the gate

```
opengrep scan --config .quality/opengrep --error \
  --exclude node_modules --exclude build --exclude dist --exclude out .
```

The CI gate (the shared `reusable-quality.yml`) runs exactly this and fails on any
finding (`--error`). Upstream registry rules are Apache-2.0 / LGPL-2.1 licensed; rule
logic is reproduced / adapted here. To refresh against upstream, diff the registry
packs and port new high-signal rules in (one-in-one-out review).
