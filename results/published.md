# Published results (real, private data)

These are the numbers from the production evaluation, restated exactly as published in
[How Evals Cut Wrong Matches in AI Web Research by 83%](https://tonytonggg.com/writing/evals-ai-web-research-crm).
The real firms, labels and pages are private; this repo ships a synthetic set with the same
composition instead (see `results/synthetic-mock/report.md` for what the code produces on it).

## Benchmark: 60 hand-labelled firms

Composition: 20 firms the system had flagged as possible mismatches (recall), 30 random unflagged
firms (accuracy: 29 of 30 were right), 10 firms left with no website (misses). Labelling took
1.5 hours.

| | Before | After |
|---|---:|---:|
| Wrong website given | 12 | **2** |
| Right websites kept (of 38) | 38 | 36 |
| "No website" firms correctly left blank (of 10) | 0 | **10** |
| Missed websites found (of 2) | 0 | 1 |
| **Right outcome (of 60)** | **46** | **55** |

- 12 of 50 websites belonged to a different business; 10 of those 12 firms had no website at all;
  2 of 10 firms left blank did have a website.
- 9 of the 12 wrong websites came from job ads with no address.
- An 83% cut in wrong websites (12 to 2); 64% fewer errors of any kind (14 to 5).

## Detectors on the same labels

| Detector | Recall on wrong websites | Precision |
|---|---|---|
| Rule check (domain shares a word with the registered name) | 7 of 12 (58%) | 7 of 11 (64%) |
| System's own mismatch flag | 11 of 12 (not usable: the 20 suspicious rows were selected by this flag) | |

Comparing the domain against the **registered** company name instead of the Maps name raised
recall on wrong matches from 2 in 10 to 6 in 10 in an early version of the check.

## Judge calibration

Jev (TypeSafe) judged 11 name-only candidates per run: it rejected all 8 wrong ones and also both
right ones (scores 0.70 and 0.40 against a 0.85 cut-off). Scores moved by at most 0.04 between runs.
The cut-off was left unchanged, because choosing it from the test labels would be tuning to the test.

## Four Claude models vs the rules (same frozen dossier: 60 firms, 103 candidate sites, 3 runs each)

| Judge | Wrong | Missed | Right (of 60) | Same answer in all 3 runs |
|---|---:|---:|---:|---:|
| Rules + Jev (TypeSafe) | 2 | 3 | 55 | 60/60 |
| Claude Haiku | 1–2 | 5–6 | 53 | 57/60 |
| Claude Sonnet | 2–3 | 1–2 | 56 | 59/60 |
| Claude Opus | 2 | 2 | 56 | 60/60 |
| Claude Fable | 2 | 3 | 55 | 60/60 |

## Fresh holdout (2026-10-21)

A new weekly run produced 244 leads, 208 new to both the tuning set and the CRM. The top 25 by lead
score went through the matching step once, live, with no changes afterwards, and were labelled by hand.

| Outcome | Firms |
|---|---:|
| Right website | 17 |
| Correctly left blank | 2 |
| Flagged for a person, right site among the options | 3 |
| Missed a real site | 1 |
| **Wrong website** | **0** |
| Label unsure (not scored) | 2 |

19 of 23 right with no human input (83%), 22 of 23 after a person picks among flagged options (96%),
0 wrong. By the rule of three the true wrong-site rate is below about 13% at 95% confidence.

## Summary

| | Before | After: benchmark (60) | After: fresh holdout (23) |
|---|---|---|---|
| **Wrong website** | 12/60 (20%) | 2/60 (3%) | **0/23** (95% bound: under 13%) |
| Right outcome, no human input | 46/60 (77%) | 55/60 (92%) | 19/23 (83%) |
| Right outcome after a person picks among flagged options | | | 22/23 (96%) |

Cost: about US$0.30 in search and enrichment calls for the whole evaluation; about US$0.05 for the
benchmark searches.
