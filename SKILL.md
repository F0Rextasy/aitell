---
name: aitell
description: Flags AI-style tells in prose with eleven deterministic pattern-count rules plus a weighted score mapped to clean/likely-human/likely-ai/ai-tells bands (full catalogue in references/RULES.md). Use when prose reads machine-polished -- before publishing, in CI on docs and posts. Exit 1 only at/above --fail-over (default ai-tells); bands describe style, NOT authorship.
license: MIT
compatibility: Requires Python 3.8+ stdlib only; no model calls, no network use, no keys. Works in Claude Code, Codex, Cursor, plus any Agent Skills compatible client.
metadata:
  author: F0Rextasy
  version: "1.0"
---

# aitell

Prose can read machine-polished without anyone noticing when it
happened: the em-dashes multiply, lists always arrive in threes,
and somehow the draft keeps inviting the reader to explore. `aitell` turns "this reads like AI"
into a counted verdict -- eleven fixed rules, a weighted score, a band.
Deterministic, milliseconds, no model judging your writing, no network.

AI-style tells, NOT proof of authorship: a band says the text *looks*
like common LLM output, never who wrote it.

## The one rule

You may not ship prose you have not scanned:

```bash
python scripts/aitell README.md posts/ --no-color
```

- **exit 1** - a file reached `--fail-over` (default `ai-tells`): rewrite or acknowledge.
- **exit 0** - every file below the gate.
- **exit 2** - usage error.

## Protocol

1. **Pick the surface** - README.md plus `posts/` (or any files/dirs; the
   walk picks up `*.md`/`*.txt`, fences stripped before analysis).
2. **Scan, never trust your ear**: eleven rules count tells with
   published thresholds (see references/RULES.md for the catalogue).
3. **Act on the band**:

| Band | Score | Blocks? |
| --- | --- | --- |
| `clean` | 0-1 | never |
| `likely-human` | 2-4 | only `--fail-over likely-human` |
| `likely-ai` | 5-7 | `--fail-over likely-ai` |
| `ai-tells` | 8+ | default gate |

4. **Report back** - file, band, score, and which rules fired with measured
   values:

```console
$ python scripts/aitell notes.md --no-color
== notes.md: AI-TELLS (score 24)
  HIT  delve                1 occurrence(s)  [threshold: >=1 occurrence]
  ok   sentence-uniformity  stdev 8.94 words over 7 sentences  [threshold: >=5 sentences and stdev < 6.0 words]
```

## Hard bans

- Never call a band proof of who wrote the text -- tells are style
  signals, and a human can trip every rule by imitating the pattern.
- Never paste prose into a model to "check" it -- counting is a solved
  problem, and this skill exists to keep your words on the machine.
- Never tune the gate to go green -- lower `--fail-over` to catch more,
  rewrite the prose to clear it, and say which in the report.

## Reporting back

1. File, band, score per file.
2. Which rules fired, with measured values vs thresholds.
3. Command and exit code.
