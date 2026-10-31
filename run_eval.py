"""Score website matchers and model judges against hand labels.

  python run_eval.py                                  # everything, mock judges, no keys, no cost
  python run_eval.py --judge claude:haiku             # real model for the yes/no step
  python run_eval.py --models haiku,sonnet,opus,fable # four-model comparison (needs ANTHROPIC_API_KEY)

Sections of the report (results/<out>/report.md):
  1. Detectors: how well a check catches wrong websites (precision / recall), and why a detector
     can't be scored on rows it selected itself.
  2. Before vs after on the 60-firm dev set: naive first-result step vs evidence-based step, N runs.
  3. Judge scores for the name-only candidates (consistency across runs, agreement at the cut-off).
  4. Model comparison: each model picks blind from the same frozen dossier, N runs, cost per model.
  5. Fresh holdout: the evidence step run once on firms it was never tuned on, with a 95% bound.
"""
import argparse
import csv
import json
from pathlib import Path

import judges
from match import dom, evidence_match, naive_match, rule_check

ROOT = Path(__file__).parent
DATA = ROOT / "data"


def load(name):
    firms = [json.loads(l) for l in (DATA / f"{name}_firms.jsonl").read_text().splitlines() if l.strip()]
    labels = {r["id"]: r for r in csv.DictReader(open(DATA / "labels" / f"{name}_labels.csv"))}
    for f in firms:
        t = labels[f["id"]]["truth_website"].strip().lower()
        f["truth"] = "unsure" if t == "unsure" else dom(t)
    return firms


PAGES = {k: v for k, v in json.loads((DATA / "pages.json").read_text()).items() if not k.startswith("_")}


def outcome(truth, answer, alts=()):
    if answer:
        return "right" if answer == truth else "wrong"
    if truth and truth in alts:
        return "flagged"  # several options, the right one among them: a person picks
    return "missed" if truth else "blank_ok"


def score_dev(firms, answers):
    """answers: {id: (website, alternatives)}. Same metrics as the published before/after table."""
    rows = {f["id"]: outcome(f["truth"], *answers[f["id"]]) for f in firms}
    old = {f["id"]: naive_match(f)["website"] for f in firms}
    got = [f for f in firms if f["group"] != "blank"]
    return {
        "wrong": sum(r == "wrong" for r in rows.values()),
        "right_kept": sum(rows[f["id"]] == "right" for f in got if f["truth"] and f["truth"] == old[f["id"]]),
        "none_rows_blank": sum(rows[f["id"]] == "blank_ok" for f in got if f["truth"] is None),
        "found_missing": sum(rows[f["id"]] == "right" for f in firms if f["group"] == "blank"),
        "missed": sum(r == "missed" for r in rows.values()),
        "right_outcome": sum(r in ("right", "blank_ok") for r in rows.values()),
        "_rows": rows,
    }


def prf(flags, firms):
    """Detector score on rows with a website: does `flag` catch the wrong ones?"""
    lab = [f for f in firms if naive_match(f)["website"]]
    wrong = {f["id"] for f in lab if naive_match(f)["website"] != f["truth"]}
    tp = sum(flags[f["id"]] and f["id"] in wrong for f in lab)
    fp = sum(flags[f["id"]] and f["id"] not in wrong for f in lab)
    fn = len(wrong) - tp
    return tp, fp, fn


def dossier(firm):
    """Frozen, blind input for a model: firm facts + every non-directory candidate, no labels."""
    from match import candidates, is_directory
    cands = candidates(firm) + [{"dom": dom(g["link"]), "source": "google", "listing_name": g["title"]} for g in firm.get("google") or []]
    seen, out = set(), []
    for c in cands:
        if not c["dom"] or c["dom"] in seen or is_directory(c["dom"]):
            continue
        seen.add(c["dom"])
        pg = PAGES.get(c["dom"])
        out.append({"domain": c["dom"], "found_via": c["source"], "listing_name": c.get("listing_name"),
                    "listing_postal_codes": c.get("listing_postals"), "site_loads": pg is not None,
                    "page_title": (pg or {}).get("title"), "page_text_excerpt": (pg or {}).get("text", "")[:1500] or None})
    return {"company": firm["company"], "uen": firm["uen"], "job_ad_address": firm["job_ad_address"] or None,
            "registry_address": f"{firm['acra'].get('street') or ''} {firm['acra'].get('postal') or ''}".strip() or None,
            "candidates": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", default="mock", help="yes/no judge inside the evidence step: mock | claude:<alias>")
    ap.add_argument("--models", default="mock", help="comma list for the comparison: mock | haiku,sonnet,opus,fable")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--out", default="results/latest")
    a = ap.parse_args()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    dev, hold = load("dev"), load("holdout")
    L = ["# Website-matching eval", "",
         "Data: SYNTHETIC firms in `data/` (same composition as the private set: 20 flagged, 30 random, "
         "10 blank, plus a 25-firm holdout). Numbers below describe the synthetic set, not production.", ""]

    # ---- 1. detectors ----
    rule = {f["id"]: rule_check(f["company"], naive_match(f)["website"]) == "flag" for f in dev}
    pipe = {f["id"]: f["pipeline_flagged"] for f in dev}
    L += ["## 1. Detectors: catching wrong websites from the old step", "",
          "| Detector | Wrong sites caught (recall) | Flags that were real (precision) |", "|---|---|---|"]
    for name, flags in (("Rule check (domain shares a word with the registered name)", rule),
                        ("Pipeline's own mismatch flag *(biased: it chose the flagged rows)*", pipe)):
        tp, fp, fn = prf(flags, dev)
        L.append(f"| {name} | {tp}/{tp + fn} ({tp / max(tp + fn, 1):.0%}) | {tp}/{tp + fp} ({tp / max(tp + fp, 1):.0%}) |")
    missed = [f["company"] for f in dev if naive_match(f)["website"] and naive_match(f)["website"] != f["truth"] and not rule[f["id"]]]
    L += ["", f"Rule-check misses (each shares one common word with the domain): {', '.join(missed)}", ""]
    rand = [f for f in dev if f["group"] == "random"]
    L += [f"Old step accuracy on the random sample only: {sum(naive_match(f)['website'] == f['truth'] for f in rand)}/{len(rand)}.", ""]

    # ---- 2. before vs after ----
    judge = judges.make(a.judge)
    before = score_dev(dev, {f["id"]: (naive_match(f)["website"], ()) for f in dev})
    runs, raw = [], []
    for _ in range(a.runs):
        res = {f["id"]: evidence_match(f, PAGES, judge) for f in dev}
        raw.append(res)
        runs.append({k: (r["website"], tuple(r["alternatives"])) for k, r in res.items()})
    after = [score_dev(dev, r) for r in runs]
    col = lambda k: ", ".join(str(s[k]) for s in after)
    n = lambda cond: sum(1 for f in dev if cond(f))
    kept = n(lambda f: f["group"] != "blank" and f["truth"] and f["truth"] == naive_match(f)["website"])
    none_rows = n(lambda f: f["group"] != "blank" and f["truth"] is None)
    miss_rows = n(lambda f: f["group"] == "blank" and f["truth"])
    same = sum(1 for f in dev if len({r[f["id"]] for r in runs}) == 1)
    L += [f"## 2. Before vs after on {len(dev)} labelled firms ({a.runs} runs, judge = {judge.name})", "",
          "| Metric | Before (first result) | After (each run) |", "|---|---:|---|",
          f"| Wrong website given | {before['wrong']} | {col('wrong')} |",
          f"| Right websites kept (of {kept}) | {before['right_kept']} | {col('right_kept')} |",
          f"| 'No website' firms correctly left blank (of {none_rows}) | {before['none_rows_blank']} | {col('none_rows_blank')} |",
          f"| Missed websites found (of {miss_rows}) | {before['found_missing']} | {col('found_missing')} |",
          f"| **Right outcome (of {len(dev)})** | **{before['right_outcome']}** | **{col('right_outcome')}** |", "",
          f"Same answer in all {a.runs} runs: {same}/{len(dev)}.", "",
          "| Firm | Scenario | Before | After (run 1) | Truth | Result |", "|---|---|---|---|---|---|"]
    for f in dev:
        b, r1 = before["_rows"][f["id"]], after[0]["_rows"][f["id"]]
        if b != r1 or r1 not in ("right", "blank_ok"):
            L.append(f"| {f['company']} | {f['scenario']} | {naive_match(f)['website'] or 'blank'} | "
                     f"{runs[0][f['id']][0] or 'blank'} | {f['truth'] or 'none'} | {b} -> {r1} |")

    # ---- 3. judge scores ----
    jrows = {}
    for res in raw:
        for f in dev:
            for j in res[f["id"]]["judged"]:
                jrows.setdefault((f["company"], j["dom"], j["dom"] == f["truth"]), []).append(j["p"])
    L += ["", f"## 3. Judge on name-only candidates (accepted at >= 0.85)", "",
          f"{len(jrows)} candidates judged per run.", "",
          "| Firm | Candidate | Score per run | Really the firm's site? |", "|---|---|---|---|"]
    for (c, d, ok), ps in sorted(jrows.items(), key=lambda x: -(x[1][0] or 0)):
        L.append(f"| {c} | {d} | {', '.join('-' if p is None else f'{p:.2f}' for p in ps)} | {'yes' if ok else 'no'} |")
    spread = max((max(ps) - min(ps) for ps in jrows.values() if None not in ps), default=0)
    L += ["", f"Largest score change between runs: {spread:.2f}. A judge needs two checks: consistency across runs, "
          "and agreement with the labels at the threshold actually used.", ""]

    # ---- 4. model comparison ----
    entries = {f["id"]: dossier(f) for f in dev}
    n_cands = sum(len(e["candidates"]) for e in entries.values())
    L += [f"## 4. Model comparison: blind pick from the same frozen dossier ({len(dev)} firms, {n_cands} candidate sites)", "",
          "| Judge | Wrong | Missed | Right (of 60) | Same answer in all runs | Calls | Cost (US$) |", "|---|---|---|---|---:|---:|---:|"]
    variants = {f"Rules + {judge.name} judge": (runs, judge)}
    for spec in [m.strip() for m in a.models.split(",") if m.strip()]:
        mj = judges.make("mock" if spec == "mock" else f"claude:{spec}")
        mruns = []
        for i in range(a.runs):
            rr = {}
            for f in dev:
                p = mj.pick(entries[f["id"]], f, PAGES)
                rr[f["id"]] = (dom(p.get("website")), ())
            mruns.append(rr)
            (out / f"models-{spec}-r{i + 1}.json").write_text(json.dumps({k: v[0] for k, v in rr.items()}, indent=1))
        variants[f"{'mock (replays the rules)' if spec == 'mock' else spec}"] = (mruns, mj)
    for name, (vr, j) in variants.items():
        ss = [score_dev(dev, r) for r in vr]
        rng = lambda k: (lambda v: str(v[0]) if len(set(v)) == 1 else f"{min(v)}-{max(v)}")([s[k] for s in ss])
        same = sum(1 for f in dev if len({r[f["id"]][0] for r in vr}) == 1)
        L.append(f"| {name} | {rng('wrong')} | {rng('missed')} | {rng('right_outcome')} | {same}/{len(dev)} | {j.calls} | {j.cost:.4f} |")
    L.append("")

    # ---- 5. holdout ----
    scored = [f for f in hold if f["truth"] != "unsure"]
    hres = {f["id"]: evidence_match(f, PAGES, judge) for f in hold}
    rows = {f["id"]: outcome(f["truth"], hres[f["id"]]["website"], hres[f["id"]]["alternatives"]) for f in scored}
    naive_wrong = sum(outcome(f["truth"], naive_match(f)["website"]) == "wrong" for f in scored)
    c = lambda k: sum(v == k for v in rows.values())
    m = len(scored)
    L += [f"## 5. Fresh holdout: {len(hold)} firms, run once, no changes afterwards", "",
          "| Outcome | Firms |", "|---|---:|",
          f"| Right website | {c('right')} |", f"| Correctly left blank | {c('blank_ok')} |",
          f"| Flagged for a person, right site among the options | {c('flagged')} |",
          f"| Missed a real site | {c('missed')} |", f"| **Wrong website** | **{c('wrong')}** |",
          f"| Label unsure (not scored) | {len(hold) - m} |", "",
          f"Right with no human input: {c('right') + c('blank_ok')}/{m}. After a person picks among flagged options: "
          f"{c('right') + c('blank_ok') + c('flagged')}/{m}.",
          f"With {c('wrong')} wrong in {m}, the rule of three puts the true wrong-site rate below {3 / m:.0%} at 95% confidence."
          if c("wrong") == 0 else f"Wrong-site rate on the holdout: {c('wrong')}/{m}.",
          f"(For reference, the old first-result step would have given {naive_wrong} wrong websites on these {m}.)", ""]
    shared = {}
    for f in hold:
        if hres[f["id"]]["website"]:
            shared.setdefault(hres[f["id"]]["website"], []).append(f["company"])
    dup = {k: v for k, v in shared.items() if len(v) > 1}
    if dup:
        L += ["Same website on several firms (a dedupe question, not a matching error): " +
              "; ".join(f"{k} <- {', '.join(v)}" for k, v in dup.items()), ""]

    (out / "report.md").write_text("\n".join(L) + "\n")
    (out / "dev-run1.json").write_text(json.dumps({k: {x: v[x] for x in ("website", "status", "method", "alternatives")}
                                                   for k, v in raw[0].items()}, indent=1))
    print("\n".join(L))
    print(f"Saved to {out.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
