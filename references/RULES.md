# Tell inventory and decision order

`scripts/aitell` scans Markdown/plain-text files with eleven fixed
regex/counting rules (no model, no network, no telemetry) and reports
per-rule hits plus a weighted total mapped to a verdict band. First the
text is stripped of fenced code blocks (code samples are never prose);
then every rule runs; first firing per rule counts once. Weights and
thresholds are constants in the script header -- change them and the
published confusion matrix in `README.md` must change too.

| # | Rule | What fires it | Weight |
| --- | --- | --- | --- |
| 1 | `delve` | >=1 `delve/delves/delved/delving` (case-insensitive) | 3 |
| 2 | `conclusion` | >=1 `in conclusion` (case-insensitive) | 2 |
| 3 | `moreover-opener` | >=1 paragraph whose first line opens with `moreover`/`furthermore` (after `#`, `>`, list markers) | 2 |
| 4 | `emdash-density` | >1.0 em/en dashes per 100 words AND >=2 dashes total (single stray dash is not evidence) | 2 |
| 5 | `triplet` | >=2 `, X, and Y` comma-triplets ("fast, reliable, and secure") | 2 |
| 6 | `notjust` | >=1 `not just X, it's Y` / `not only X but Y` (up to 80 chars between halves) | 3 |
| 7 | `divein` | >=1 `let's dive in` / `let us dive in` / `dive (right) in` (case-insensitive) | 3 |
| 8 | `boldheaders` | >=2 lines that are entirely `**bold**` (headers-as-emphasis pattern) | 1 |
| 9 | `verb-cluster` | >=2 `unlock/harness/leverage` word forms (case-insensitive) | 2 |
| 10 | `emoji-bullets` | >=2 bullets and >=30% carry emoji/codepoint >= U+1F000 or in dingbat ranges | 2 |
| 11 | `sentence-uniformity` | >=5 sentences and stdev of sentence length < 6.0 words | 2 |

## Verdict bands

| Band | Score | Exit effect |
| --- | --- | --- |
| `clean` | 0-1 | never blocks |
| `likely-human` | 2-4 | blocks only with `--fail-over likely-human` |
| `likely-ai` | 5-7 | blocks with `--fail-over likely-ai` |
| `ai-tells` | 8+ | blocks by default (`--fail-over ai-tells`) |

Band names describe STYLE, not authorship. `ai-tells` means the prose
contains patterns common in LLM output -- NOT proof a machine wrote it,
and never a plagiarism or cheating verdict. Exit 1 only when a file
reaches `--fail-over` (CI use); exit 2 is usage error (unreadable path,
no text files found, bad flags).

## Output

Text: one `== file: BAND (score N)` header per file, one `HIT/ok` row
per rule with the measured value and its threshold. `--format json` for
machines:

```json
{"ok": false, "fail_over": "ai-tells", "worst": "ai-tells",
 "files": [{"file": "notes.md", "verdict": "ai-tells", "score": 24,
            "hits": {"delve": {"fired": true, "measured": "1 occurrence(s)"}}}]}
```

## Design invariants

- Verdicts are a pure function of file bytes -- same input, same
  answer, no sampling, no model, no network.
- Code fences are stripped before analysis; markup elsewhere is inert
  (rules match words/dashes/emoji, not formatting).
- A single dash, triplet, or bold line never fires alone: every density
  rule has a count floor so ordinary prose stays `clean`.
