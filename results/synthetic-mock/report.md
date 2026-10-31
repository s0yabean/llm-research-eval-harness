# Website-matching eval

Data: SYNTHETIC firms in `data/` (same composition as the private set: 20 flagged, 30 random, 10 blank, plus a 25-firm holdout). Numbers below describe the synthetic set, not production.

## 1. Detectors: catching wrong websites from the old step

| Detector | Wrong sites caught (recall) | Flags that were real (precision) |
|---|---|---|
| Rule check (domain shares a word with the registered name) | 7/12 (58%) | 7/11 (64%) |
| Pipeline's own mismatch flag *(biased: it chose the flagged rows)* | 11/12 (92%) | 11/20 (55%) |

Rule-check misses (each shares one common word with the domain): QV CLEANING PTE. LTD., TEOW HOCK PLUMBING AND DESIGN, BLUE ELECTRA PTE. LTD., JW INTERIOR RENOVATION & CONSTRUCTION PTE. LTD., MONARCH EFFECT PTE. LTD.

Old step accuracy on the random sample only: 29/30.

## 2. Before vs after on 60 labelled firms (3 runs, judge = mock)

| Metric | Before (first result) | After (each run) |
|---|---:|---|
| Wrong website given | 12 | 2, 2, 2 |
| Right websites kept (of 38) | 38 | 36, 36, 36 |
| 'No website' firms correctly left blank (of 10) | 0 | 10, 10, 10 |
| Missed websites found (of 2) | 0 | 1, 1, 1 |
| **Right outcome (of 60)** | **46** | **55, 55, 55** |

Same answer in all 3 runs: 60/60.

| Firm | Scenario | Before | After (run 1) | Truth | Result |
|---|---|---|---|---|---|
| PROWYSH CLEANING SERVICE PTE. LTD. | marketplace instead of the firm | helpnest.com.sg | blank | none | wrong -> blank_ok |
| SEVEN LOTUS BEAUTY SALON PTE. LTD. | review directory as the website | reviewhive.website | blank | none | wrong -> blank_ok |
| ORBITANE DYNAMICS PTE. LTD. | the mall, not the tenant | marinavistamall.com.sg | blank | none | wrong -> blank_ok |
| METRONDO PTE. LTD. | lookalike name, different business | latrondo.com | blank | none | wrong -> blank_ok |
| LOGIQUAY WAREHOUSING PTE. LTD. | neighbour in the same building | ylvane.com | blank | none | wrong -> blank_ok |
| RMQ LOGISTICS & SERVICES PTE. LTD. | foreign lookalike | rmxfreighthouston.com | blank | none | wrong -> blank_ok |
| QV CLEANING PTE. LTD. | common word: 'cleaning' | sgcleaningpros.co | blank | none | wrong -> blank_ok |
| TEOW HOCK PLUMBING AND DESIGN | common word: 'hock' | hockwell.com | blank | none | wrong -> blank_ok |
| BLUE ELECTRA PTE. LTD. | common word: 'blue' | blueryde.com.sg | blank | none | wrong -> blank_ok |
| HALVERA LAB PTE. LTD. | wrong URL in the job ad itself | lumivane.com | lumivane.com | halveraloft.com.sg | wrong -> wrong |
| JW INTERIOR RENOVATION & CONSTRUCTION PTE. LTD. | lookalike name (two of them) | jwcinterior.com | jwinteriorsg.com | jwinterior.sg | wrong -> wrong |
| XANTHE BEAUTY SALONS PTE. LTD. | trading name differs from registered name | xanhairsg.com | blank | xanhairsg.com | right -> missed |
| MONARCH EFFECT PTE. LTD. | common word: 'monarch' | monarchvale.sg | blank | none | wrong -> blank_ok |
| DR KELLAN PTE. LTD. | right site, name-only evidence (judge too strict) | drkellan.com | blank | drkellan.com | right -> missed |
| PREMIER IRONWOOD RESOURCES | missed site, found by search (UEN on site) | blank | premierironwood.sg | premierironwood.sg | missed -> right |
| PERIWYNKLE SINGAPORE PTE. LTD. | missed site, name-only evidence | blank | blank | periwynkle.asia | missed -> missed |

## 3. Judge on name-only candidates (accepted at >= 0.85)

10 candidates judged per run.

| Firm | Candidate | Score per run | Really the firm's site? |
|---|---|---|---|
| QV CLEANING PTE. LTD. | qvcleaningtools.com | 0.70, 0.70, 0.70 | no |
| DR KELLAN PTE. LTD. | drkellan.com | 0.70, 0.70, 0.70 | yes |
| PROWYSH CLEANING SERVICE PTE. LTD. | prowyshpro.sg | 0.55, 0.55, 0.55 | no |
| PERIWYNKLE SINGAPORE PTE. LTD. | periwynkle.asia | 0.55, 0.55, 0.55 | yes |
| RMQ LOGISTICS & SERVICES PTE. LTD. | jobbeeq.com | 0.30, 0.30, 0.30 | no |
| PSALTER FAMILY CLINIC PTE. LTD. | clinicbookr.sg | 0.30, 0.30, 0.30 | no |
| KORRIN CLEAN PTE. LTD. | korrinclean.com | 0.30, 0.30, 0.30 | no |
| MONARCH EFFECT PTE. LTD. | runclubhub.sg | 0.15, 0.15, 0.15 | no |
| FENGWEI PTE. LTD. | fengweipalace.com.sg | 0.15, 0.15, 0.15 | no |
| VANTRO TECH PTE. LTD. | jobbeeq.com | 0.01, 0.01, 0.01 | no |

Largest score change between runs: 0.00. A judge needs two checks: consistency across runs, and agreement with the labels at the threshold actually used.

## 4. Model comparison: blind pick from the same frozen dossier (60 firms, 61 candidate sites)

| Judge | Wrong | Missed | Right (of 60) | Same answer in all runs | Calls | Cost (US$) |
|---|---|---|---|---:|---:|---:|
| Rules + mock judge | 2 | 3 | 55 | 60/60 | 30 | 0.0000 |
| mock (replays the rules) | 2 | 3 | 55 | 60/60 | 180 | 0.0000 |

## 5. Fresh holdout: 25 firms, run once, no changes afterwards

| Outcome | Firms |
|---|---:|
| Right website | 17 |
| Correctly left blank | 2 |
| Flagged for a person, right site among the options | 3 |
| Missed a real site | 1 |
| **Wrong website** | **0** |
| Label unsure (not scored) | 2 |

Right with no human input: 19/23. After a person picks among flagged options: 22/23.
With 0 wrong in 23, the rule of three puts the true wrong-site rate below 13% at 95% confidence.
(For reference, the old first-result step would have given 4 wrong websites on these 23.)

Same website on several firms (a dedupe question, not a matching error): corvane.sg <- CORVANE HOLDINGS PTE. LTD., CORVANE SERVICES PTE. LTD.

