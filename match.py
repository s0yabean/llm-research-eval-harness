"""Two ways to find a company's own website from a job ad.

naive_match     The original step: use the URL in the job ad, otherwise the website of the
                first Google Maps result for the company name. A search rank is treated as
                evidence, so a wrong listing is accepted along with its own website.

evidence_match  The rebuilt step. A candidate counts only when something ties it to the
                *registered* company: the job ad gave the URL, the Maps listing carries the
                full registered name, the listing's postal code matches the job ad / registry
                address AND the names share a distinctive word, or the site itself shows the
                UEN, the full registered name, or the postal code plus a name match.
                Name-only matches go to a yes/no judge (pluggable, see judges.py).
                Nothing firm-tied -> one web search under the same rules -> otherwise blank.

rule_check      The cheap detector that existed before: does the domain share a word with
                the registered name? Used only to score how well a check catches wrong sites.

All inputs are frozen (data/*.jsonl + data/pages.json), so repeated runs see identical
searches and pages and only the judge can vary.
"""
import re

# Social, job boards, directories, marketplaces: research links, never the firm's own site.
# Generic platforms plus the fictional ones used in the synthetic data.
DIRECTORY = re.compile(
    r"(^|\.)(facebook|instagram|linkedin|tiktok|youtube|twitter|x|google|goo|wa|linktr|bit|"
    r"business\.site|indeed|glassdoor|jobstreet|yelp|tripadvisor|wikipedia|crunchbase|zoominfo|"
    r"yellowpages|amazon|shopee|lazada|"
    r"helpnest|reviewhive|bizdirsg|sgfirmlist|clinicfinder)\.[a-z.]+$"
)

# Words too common in company names to identify a firm on their own.
GENERIC = set((
    "pte ltd llp llc private limited singapore sg the and of co company services service group holdings "
    "enterprise enterprises trading international asia pacific global solutions solution management "
    "consultancy consulting consultants centre center studio clinic medical dental health healthcare beauty "
    "salon salons spa hair aesthetic aesthetics cleaning clean renovation renovations interior interiors design "
    "designs construction engineering engineers contractor contractors builders build builds plumbing electrical "
    "electric aircon air con logistics logistic freight transport movers moving warehousing supplies supply "
    "marketing tuition learning education enrichment academy school training care family systems system "
    "technology technologies tech digital media resources industries industrial food foods cafe restaurant "
    "kitchen bakery cakes facilities facility property properties realty home homes office"
).split())

BUILDING = re.compile(r"mall|shopping cent|plaza|office building|commercial building|business park|"
                      r"industrial (estate|park)|hotel|condominium|apartment", re.I)

JUDGE_THRESHOLD = 0.85  # left where it was set before the labels existed (see README)


def dom(u):
    """'https://www.Example.com.sg/contact' -> 'example.com.sg'; blank / 'none' -> None."""
    u = (u or "").strip().lower()
    if not u or u in ("none", "null"):
        return None
    d = u.split("//")[-1].split("/")[0].split("?")[0].split("#")[0]
    return d[4:] if d.startswith("www.") else d


def is_directory(d):
    return bool(d) and bool(DIRECTORY.search(d))


def words(s):
    return re.findall(r"[a-z0-9]+", (s or "").lower().replace("&", " and "))


def norm_name(s):
    s = re.sub(r"\b(pte|ltd|llp|private|limited|singapore|sg)\b", "", (s or "").lower())
    return re.sub(r"[^a-z0-9]", "", s)


def postals_in(s):
    return set(re.findall(r"\b\d{6}\b", s or ""))


def firm_facts(firm):
    acra = firm.get("acra") or {}
    job_postal = (firm.get("job_ad_address") or "").split(" ")[-1]
    postals = {p for p in (job_postal, acra.get("postal")) if re.fullmatch(r"\d{6}", p or "")}
    short = re.sub(r"\b(PTE\.?|LTD\.?|PRIVATE|LIMITED|LLP|SINGAPORE)", "", firm["company"], flags=re.I)
    short = re.sub(r"\s+", " ", re.sub(r"[().]", " ", short)).strip()
    distinct = [norm_name(w) for w in words(short) if w not in GENERIC and len(w) >= 2]
    return {
        "postals": postals,
        # Full registered name as whole words, legal suffix included ("dr frigo pte ltd"):
        # "Doctor Frigo Pte Ltd" is a different firm.
        "name_phrase": " ".join(words(re.sub(r"\bprivate limited\b", "pte ltd", firm["company"], flags=re.I))),
        "distinct": [d for d in distinct if d],
        "joined": norm_name(short),
        "short": short,
        "acra_street": (acra.get("street") or "").lower(),
    }


def evidence(firm, facts, cand, pages):
    """Firm-tied signals for one candidate. Facts that come from the same listing as the
    candidate (its own phone, its own name) don't count on their own."""
    pg = pages.get(cand["dom"])
    text = (pg or {}).get("text", "").lower()
    flat = re.sub(r"[^a-z0-9]", "", text)
    tokens = " " + " ".join(words(text)) + " "
    ev = {}
    if cand.get("listing_name") is not None and cand["source"].startswith("maps"):
        ln = norm_name(f"{cand['listing_name']} {cand['dom']}")
        initials = "".join(w[0] for w in words(cand["listing_name"]) if w not in ("pte", "ltd", "llp"))
        # Postal code alone isn't enough: malls and industrial buildings have many tenants.
        tie = ((not facts["distinct"] and len(facts["joined"]) >= 6 and facts["joined"] in ln)
               or any(len(w) >= 3 and w in ln for w in facts["distinct"])
               or any(len(w) >= 2 and initials.startswith(w) for w in facts["distinct"]))
        postal = bool(set(cand.get("listing_postals") or []) & facts["postals"])
        ev["listing_postal"] = postal and tie
        ev["listing_tie"] = tie
        ev["postal_only"] = postal and not tie
        ev["listing_full_name"] = f" {facts['name_phrase']} " in " " + " ".join(words(cand["listing_name"])) + " "
    if pg:
        uen = (firm.get("uen") or "").lower()
        ev["uen_on_site"] = bool(uen) and uen in flat
        ev["name_on_site"] = len(facts["name_phrase"].split()) >= 2 and f" {facts['name_phrase']} " in tokens
        ev["postal_on_site"] = any(p in text for p in facts["postals"])
        ev["singapore"] = bool(re.search(r"singapore|\+65|\(65\)", text)) or cand["dom"].endswith(".sg")
    ev["site_loads"] = pg is not None
    hay = norm_name(f"{cand['dom']} {cand.get('listing_name') or ''} {(pg or {}).get('title', '')}")
    # Every distinctive word of the name in the domain, listing name or page title (weak: needs the judge).
    # Names made only of common words have no distinctive word: match the whole name joined.
    ev["name_match"] = (all(w in hay for w in facts["distinct"]) if facts["distinct"]
                        else len(facts["joined"]) >= 6 and facts["joined"] in hay)
    # A postal code printed on the site only counts with a name tie too (every mall tenant shows it).
    ev["postal_tie"] = bool(ev.get("postal_on_site")) and bool(ev.get("listing_tie") or ev["name_match"])
    ev["strong"] = bool(ev.get("listing_postal") or ev.get("listing_full_name") or ev.get("uen_on_site")
                        or ev.get("name_on_site") or ev["postal_tie"] or cand["source"] == "job ad")
    ev["foreign"] = (ev["site_loads"] and not ev.get("singapore") and not ev.get("uen_on_site")
                     and not ev["postal_tie"] and not ev.get("listing_postal") and not ev.get("listing_full_name"))
    return ev


def _decide(firm, facts, scored, method, judge, pages, judged):
    usable = [c for c in scored if not c["ev"]["foreign"]]
    strong = [c for c in usable if c["ev"]["strong"]]
    doms = list(dict.fromkeys(c["dom"] for c in strong))
    if len(doms) == 1:
        return {"website": doms[0], "status": "found", "method": f"{method}: {strong[0]['source']}"}
    if len(doms) > 1:
        best = list(dict.fromkeys(c["dom"] for c in strong if c["ev"].get("uen_on_site") or c["ev"].get("name_on_site")))
        if len(best) == 1:
            return {"website": best[0], "status": "found", "method": f"{method}: UEN/name on site"}
        return {"website": None, "status": "ambiguous", "method": method, "alternatives": doms}
    yes = []
    for c in usable:
        if c["ev"]["name_match"] and c["ev"]["site_loads"]:
            p = judge.own_site(firm, c, pages.get(c["dom"]))
            c["judge_p"] = p
            judged.append({"dom": c["dom"], "p": p})
            if p is not None and p >= JUDGE_THRESHOLD:
                yes.append(c["dom"])
    yes = list(dict.fromkeys(yes))
    if len(yes) == 1:
        return {"website": yes[0], "status": "found", "method": f"{method}: judge"}
    if len(yes) > 1:
        return {"website": None, "status": "ambiguous", "method": f"{method}: judge", "alternatives": yes}
    return None


def candidates(firm):
    """Job-ad URL plus the top three Maps results (searched with the postal code)."""
    out = []
    if firm.get("job_ad_url"):
        out.append({"dom": dom(firm["job_ad_url"]), "source": "job ad"})
    for i, it in enumerate((firm.get("maps") or [])[:3]):
        if it.get("website"):
            out.append({"dom": dom(it["website"]), "source": f"maps #{i + 1}", "listing_name": it["name"],
                        # A listing for the building itself shares every tenant's postal code: no evidence.
                        "listing_postals": [] if BUILDING.search(it.get("category") or "") else sorted(postals_in(it.get("address")))})
    return [c for c in out if c["dom"]]


def evidence_match(firm, pages, judge):
    facts = firm_facts(firm)
    judged, directories = [], []

    def score(cands):
        kept = []
        for c in cands:
            if is_directory(c["dom"]):
                directories.append(c["dom"])
                continue
            c["ev"] = evidence(firm, facts, c, pages)
            kept.append(c)
        return kept

    scored = score(candidates(firm))
    pick = _decide(firm, facts, scored, "maps/job ad", judge, pages, judged)
    if not pick:  # nothing tied to the firm: one web search, same rules
        seen = {c["dom"] for c in scored}
        g = []
        for r in firm.get("google") or []:
            d = dom(r["link"])
            if d and d not in seen:
                seen.add(d)
                g.append({"dom": d, "source": "google", "listing_name": r.get("title")})
        gs = score(g)
        pick = _decide(firm, facts, gs, "google", judge, pages, judged)
        scored += gs
    pick = pick or {"website": None, "status": "none", "method": "no firm-tied candidate"}
    pick.setdefault("alternatives", [])
    pick.update({"candidates": [{k: v for k, v in c.items()} for c in scored], "directories": directories, "judged": judged})
    return pick


def naive_match(firm, pages=None, judge=None):
    """The original step: job-ad URL, else the first Maps result's website. Never blank by choice."""
    if firm.get("job_ad_url"):
        return {"website": dom(firm["job_ad_url"]), "status": "found", "method": "job ad", "alternatives": []}
    maps = firm.get("maps") or []
    if maps and maps[0].get("website"):
        return {"website": dom(maps[0]["website"]), "status": "found", "method": "maps #1", "alternatives": []}
    return {"website": None, "status": "none", "method": "no listing website", "alternatives": []}


# ---- the pre-existing rule check (a detector, scored separately) ----
STOP = {"pte", "ltd", "llp", "llc", "private", "limited", "singapore", "sg", "the", "and", "co", "company",
        "services", "service", "group", "holdings", "enterprise", "enterprises", "trading", "international",
        "asia", "pacific", "centre", "center", "studio", "clinic", "s"}
SUFFIXES = {"com", "sg", "org", "net", "edu", "gov", "co", "io", "my", "biz", "info", "asia"}


def _labels(d):
    parts = d.split(".")[:-1] or d.split(".")
    return [p for p in parts if p not in SUFFIXES and p != "www"] or parts[:1]


def _label_matches(label, name):
    label = re.sub(r"[^a-z0-9]", "", label)
    toks = {t for t in re.findall(r"[a-z0-9]+", name.lower()) if t not in STOP and len(t) > 1}
    if any(len(t) >= 3 and t in label for t in toks):
        return True
    if len(label) >= 4 and label in "".join(re.findall(r"[a-z0-9]+", name.lower())):
        return True
    ws = [w for w in re.findall(r"[a-z0-9]+", name.lower()) if w not in STOP]
    if len(ws) >= 2:
        for a in ("".join(w[0] for w in ws), ws[0] + "".join(w[0] for w in ws[1:])):
            if len(label) >= 2 and (label.startswith(a) or (len(label) >= 3 and a.startswith(label))):
                return True
    return False


def rule_check(company, website):
    """'flag' if the domain shares no word with the REGISTERED name (not the Maps name: that
    comes from the same lookup as the website, so a wrong match agrees with itself)."""
    d = dom(website)
    if not d:
        return "na"
    if is_directory(d):
        return "flag"
    return "pass" if any(_label_matches(l, company) for l in _labels(d)) else "flag"
