"""Build the SYNTHETIC eval data: every company, domain, UEN, address and page here is invented.

The set mirrors the *method* (and the composition) of the real, private golden set:

  dev (60)      20 "flagged"  rows the old pipeline marked as possible mismatches  -> measures recall
                30 "random"   unflagged rows                                        -> measures accuracy
                10 "blank"    rows the old step left with no website                -> measures misses
  holdout (25)  fresh firms the rules were never tuned on; 2 labelled "unsure"

Each row carries `scenario`: the failure type it reproduces (marketplace, mall, neighbour in the
same building, foreign lookalike, wrong URL in the job ad, common-word collision, ...). Postal codes
are in the 9xxxxx range, which no real Singapore address uses. UENs start with "SYN".

    python data/build_synthetic.py      # rewrites data/*.jsonl, data/pages.json, data/labels/*.csv
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).parent
pages = {}
dev, hold, labels_dev, labels_hold = [], [], [], []
_n = [0]


def page(d, title, text):
    pages[d] = {"title": title, "text": text}


def firm(rows, labels, fid, group, company, scenario, truth, *, industry, address="", acra_postal=None,
         acra_street="", job_ad_url=None, maps=(), google=(), note=""):
    _n[0] += 1
    rows.append({
        "id": fid, "group": group, "scenario": scenario, "company": company, "uen": f"SYN{_n[0]:05d}K",
        "industry": industry, "job_ad_address": address,
        "acra": {"name": company, "street": acra_street, "postal": acra_postal or (address.split(" ")[-1] if address else None)},
        "job_ad_url": job_ad_url, "maps": list(maps), "google": list(google),
        "pipeline_flagged": group == "flagged",
    })
    labels.append({"id": fid, "group": group, "company": company, "truth_website": truth or "none", "label_note": note})
    return rows[-1]


def M(name, address, website=None, category=""):
    return {"name": name, "address": address, "website": website, "category": category}


def G(title, link):
    return {"title": title, "link": link}


def D(*a, **k):
    return firm(dev, labels_dev, *a, **k)


def H(*a, **k):
    return firm(hold, labels_hold, *a, **k)

# =====================================================================================
# DEV: 20 flagged rows (11 wrong websites + 9 right ones)
# =====================================================================================
D("D01", "flagged", "PROWYSH CLEANING SERVICE PTE. LTD.", "marketplace instead of the firm", None,
  industry="cleaning", acra_postal="910001", acra_street="mock lane 1",
  maps=[M("Helpnest - Home Cleaning", "Somewhere Rd, Singapore 912345", "https://helpnest.com.sg")],
  google=[G("Helpnest - Book a cleaner", "https://helpnest.com.sg/cleaners"),
          G("ProWysh Pro Car Detailing", "https://prowyshpro.sg")],
  note="No own website; marketplace listing only.")
page("helpnest.com.sg", "Helpnest | Book trusted home cleaners", "Marketplace for home cleaning in Singapore. Compare 500 vetted cleaners.")
page("prowyshpro.sg", "ProWysh Pro Car Detailing", "Car detailing and polish in Singapore. Ceramic coating packages.")

D("D02", "flagged", "SEVEN LOTUS BEAUTY SALON PTE. LTD.", "review directory as the website", None,
  industry="facial", address="12 MOCK AVENUE 3 920002",
  maps=[M("Seven Lotus Beauty Salon", "12 Mock Ave 3, #01-02, Singapore 920002", "https://reviewhive.website/seven-lotus")],
  google=[G("Seven Lotus Beauty Salon reviews", "https://reviewhive.website/seven-lotus")],
  note="Only a review-directory page.")

D("D03", "flagged", "ORBITANE DYNAMICS PTE. LTD.", "the mall, not the tenant", None,
  industry="trading", address="3 MOCK BOULEVARD 930003",
  maps=[M("Marina Vista Mall", "3 Mock Blvd, Singapore 930003", "https://marinavistamall.com.sg", "Shopping mall")],
  note="Firm is a tenant of the mall; no own website.")
page("marinavistamall.com.sg", "Marina Vista Mall", "Singapore's waterfront mall. 3 Mock Boulevard, Singapore 930003. Tenant directory, parking, events.")

D("D04", "flagged", "METRONDO PTE. LTD.", "lookalike name, different business", None,
  industry="renovation", acra_postal="940004", acra_street="mock road 4",
  maps=[M("Latrondo Italian Kitchen", "88 Other St, Singapore 941234", "https://latrondo.com")],
  note="Different business with a similar name.")
page("latrondo.com", "Latrondo Italian Kitchen", "Wood-fired pizza and pasta in Singapore. Reserve a table.")

D("D05", "flagged", "LOGIQUAY WAREHOUSING PTE. LTD.", "neighbour in the same building", None,
  industry="warehousing", address="8 MOCK CRESCENT 950005",
  maps=[M("Ylvane Transport", "8 Mock Cres, #04-11, Singapore 950005", "https://ylvane.com")],
  note="Listing is another tenant of the same industrial building.")
page("ylvane.com", "Ylvane Transport", "Lorry rental and transport. 8 Mock Crescent #04-11 Singapore 950005.")

D("D06", "flagged", "RMQ LOGISTICS & SERVICES PTE. LTD.", "foreign lookalike", None,
  industry="logistics", acra_postal="950006", acra_street="mock way 6",
  maps=[M("RMX Freight Houston", "1200 Freight Rd, Houston, TX 77032", "https://rmxfreighthouston.com")],
  google=[G("RMQ Logistics & Services jobs - JobBeeq", "https://jobbeeq.com/company/rmq-logistics")],
  note="US freight company; firm has no website.")
page("rmxfreighthouston.com", "RMX Freight | Houston freight forwarding", "Air and ocean freight from Houston, Texas.")
page("jobbeeq.com", "RMQ Logistics & Services jobs - JobBeeq", "Job openings in Singapore. Apply now for logistics roles.")

D("D07", "flagged", "QV CLEANING PTE. LTD.", "common word: 'cleaning'", None,
  industry="cleaning", acra_postal="960007", acra_street="mock drive 7",
  maps=[M("SG Cleaning Pros", "5 Elsewhere Rd, Singapore 961007", "https://sgcleaningpros.co")],
  google=[G("QV Cleaning Tools | Mops and brushes", "https://qvcleaningtools.com")],
  note="Shares only the word 'cleaning'.")
page("sgcleaningpros.co", "SG Cleaning Pros", "Office cleaning across Singapore.")
page("qvcleaningtools.com", "QV Cleaning Tools", "Cleaning tools online store, Singapore.")

D("D08", "flagged", "TEOW HOCK PLUMBING AND DESIGN", "common word: 'hock'", None,
  industry="plumbing", acra_postal="960008", acra_street="mock walk 8",
  maps=[M("Hock Well Hardware", "16 Some Rd, Singapore 961008", "https://hockwell.com")],
  note="Different business sharing one word.")
page("hockwell.com", "Hock Well Hardware", "Hardware and tools in Singapore.")

D("D09", "flagged", "BLUE ELECTRA PTE. LTD.", "common word: 'blue'", None,
  industry="electrical", acra_postal="960009", acra_street="mock close 9",
  maps=[M("BlueRyde Car Sharing", "1 Car Park Rd, Singapore 961009", "https://blueryde.com.sg")],
  note="Car-sharing service sharing one word with an electrical contractor.")
page("blueryde.com.sg", "BlueRyde | Electric car sharing", "Electric car sharing in Singapore.")

D("D10", "flagged", "HALVERA LAB PTE. LTD.", "wrong URL in the job ad itself", "halveraloft.com.sg",
  industry="skincare", acra_postal="960010", acra_street="mock square 10",
  job_ad_url="https://www.lumivane.com",
  note="Employer typed a distributed brand's URL; own site is halveraloft.com.sg.")
page("lumivane.com", "Lumivane | Korean skincare", "Lumivane skincare, distributed in Singapore by partners.")
page("halveraloft.com.sg", "Halvera Loft", "Halvera Lab Pte Ltd. Skincare studio, Singapore 960010.")

D("D11", "flagged", "JW INTERIOR RENOVATION & CONSTRUCTION PTE. LTD.", "lookalike name (two of them)", "jwinterior.sg",
  industry="renovation", acra_postal="960011", acra_street="mock link 11",
  maps=[M("JWC Interior Design", "2 Far Rd, Singapore 961011", "https://jwcinterior.com"),
        M("JW Interior Renovation & Construction Pte Ltd", "9 Other Ave, Singapore 961111", "https://jwinteriorsg.com")],
  note="Real site jwinterior.sg is not among the candidates; both listings are other firms.")
page("jwcinterior.com", "JWC Interior Design", "Interior design studio in Singapore.")
page("jwinteriorsg.com", "JW Interior Renovation & Construction", "Renovation contractor, Singapore.")

D("D12", "flagged", "XANTHE BEAUTY SALONS PTE. LTD.", "trading name differs from registered name", "xanhairsg.com",
  industry="hair", address="12 MOCK STREET 960012",
  maps=[M("Xan Hair Studio", "12 Mock St, #01-12, Singapore 960012", "https://xanhairsg.com")],
  note="Same address, unit and postal code; trades as Xan Hair.")
page("xanhairsg.com", "Xan Hair Studio", "Hair colouring and cuts. 12 Mock Street #01-12 Singapore 960012.")

D("D13", "flagged", "DR. FRIGO PTE. LTD.", "right site is down; a similar-name firm is up", "doctorfrigo.sg",
  industry="aircon", address="1 MOCK LANE 960013",
  maps=[M("Dr. Frigo Asia", "1 Mock Ln, #06-01, Singapore 960013", "https://doctorfrigo.sg"),
        M("Doctor Frigo Pte Ltd", "11 Far Close, Singapore 961113", "https://doctorfrigosg.com")],
  note="Listing at the job-ad postal code; site was down when checked.")
page("doctorfrigosg.com", "Doctor Frigo Pte Ltd | aircon service", "Doctor Frigo Pte Ltd. Aircon servicing in Singapore. 11 Far Close.")

D("D14", "flagged", "TAN BROTHERS HOLDINGS PTE. LTD.", "trading brand, UEN on site", "brickloftreno.sg",
  industry="renovation", address="14 MOCK ROAD 960014",
  maps=[M("Brickloft Renovation", "14 Mock Rd, Singapore 960014", "https://brickloftreno.sg")],
  note="UEN in the site footer.")

D("D15", "flagged", "MARRISH TRADING PTE. LTD.", "URL from the job ad", "marrish.com.sg",
  industry="trading", job_ad_url="https://marrish.com.sg", acra_postal="960015")
page("marrish.com.sg", "Marrish Trading", "Food ingredients importer, Singapore.")

D("D16", "flagged", "QUILLMERE BAKERY PTE. LTD.", "registered name on site", "quillmere.com",
  industry="bakery", acra_postal="960016",
  maps=[M("Quillmere Bakes", "6 Other Rd, Singapore 961016", "https://quillmere.com")])
page("quillmere.com", "Quillmere Bakes", "Sourdough and pastries. (c) 2026 Quillmere Bakery Pte Ltd, Singapore.")

D("D17", "flagged", "SOLVANE AIRCON SERVICES PTE. LTD.", "listing carries the full registered name", "solvaneaircon.sg",
  industry="aircon", acra_postal="960017",
  maps=[M("Solvane Aircon Services Pte Ltd", "7 Other Rd, Singapore 961017", "https://solvaneaircon.sg")])
page("solvaneaircon.sg", "Solvane Aircon", "Aircon servicing in Singapore.")

D("D18", "flagged", "GRENFORD DENTAL CLINIC PTE. LTD.", "listing postal code + name tie", "grenforddental.sg",
  industry="dental", acra_postal="960018",
  maps=[M("Grenford Dental", "18 Mock Way, #02-01, Singapore 960018", "https://grenforddental.sg")])
page("grenforddental.sg", "Grenford Dental", "Family dentistry in Singapore.")

D("D19", "flagged", "SEET & VOON MEDICAL PTE. LTD.", "trading name differs; registered name on site", "harbourvaneclinic.sg",
  industry="clinic", address="19 MOCK STREET 960019",
  maps=[M("Harbourvane Family Clinic", "19 Mock St, #01-19, Singapore 960019", "https://harbourvaneclinic.sg")])
page("harbourvaneclinic.sg", "Harbourvane Family Clinic", "GP clinic. Operated by Seet & Voon Medical Pte. Ltd. Singapore.")

D("D20", "flagged", "ORCHID PEAK HOLDINGS PTE. LTD.", "trading brand, UEN on site", "tesselpilates.sg",
  industry="pilates", address="20 MOCK ROAD 960020",
  maps=[M("Tessel Pilates", "20 Mock Rd, Singapore 960020", "https://tesselpilates.sg")])

# UEN-on-site pages need the UEN, which is assigned in order above.
uen = {r["id"]: r["uen"] for r in dev}
page("brickloftreno.sg", "Brickloft Renovation", f"HDB and condo renovation. Brickloft is a brand of Tan Brothers. UEN {uen['D14']}. Singapore.")
page("tesselpilates.sg", "Tessel Pilates", f"Reformer pilates classes in Singapore. UEN {uen['D20']}.")

# =====================================================================================
# DEV: 30 random rows (29 right, 1 wrong)
# =====================================================================================
D("R01", "random", "MONARCH EFFECT PTE. LTD.", "common word: 'monarch'", None,
  industry="enrichment", acra_postal="970001", acra_street="mock rise 1",
  maps=[M("Monarchvale Events", "3 Event Rd, Singapore 971001", "https://monarchvale.sg")],
  google=[G("Monarch Effect Run 2026 | RunClubHub", "https://runclubhub.sg/events/monarch-effect")],
  note="Events company sharing one word; firm has no website.")
page("monarchvale.sg", "Monarchvale Events | Corporate events", "Corporate events in Singapore.")
page("runclubhub.sg", "Monarch Effect Run 2026 | RunClubHub", "Event registration for community runs in Singapore.")

D("R02", "random", "DR KELLAN PTE. LTD.", "right site, name-only evidence (judge too strict)", "drkellan.com",
  industry="aesthetic", acra_postal="970099", acra_street="mock hill 2",
  maps=[M("Dr Kellan Aesthetics", "2 Clinic Rd, #03-02, Singapore 970002", "https://drkellan.com")],
  note="Phone on site matches the job ad; registered office is elsewhere.")
page("drkellan.com", "Dr Kellan Aesthetics", "Aesthetic treatments in Singapore. Book a consultation.")

RANDOM = [  # (name, industry, method)
    ("BRIGHTMOSS RENOVATION", "renovation", "job_ad"), ("KELVARA AIRCON", "aircon", "listing_postal"),
    ("VELLOQUAY LOGISTICS", "logistics", "name_on_site"), ("ORRINBAY PLUMBING", "plumbing", "listing_full_name"),
    ("LUMACREST DENTAL", "dental", "uen_on_site"), ("PINEWICK MOVERS", "movers", "postal_tie"),
    ("QUORLINE TUITION", "tuition", "job_ad"), ("MARROWGATE BAKERY", "bakery", "listing_postal"),
    ("TESSWELL CLEANING", "cleaning", "name_on_site"), ("CORVANTIS ENGINEERING", "engineering", "listing_full_name"),
    ("DUNMERE ELECTRICAL", "electrical", "uen_on_site"), ("HALCYRA BEAUTY", "beauty", "postal_tie"),
    ("SORRELBY INTERIOR", "interior", "job_ad"), ("WEXMOOR TRADING", "trading", "listing_postal"),
    ("PELLCREST PEST CONTROL", "pest", "name_on_site"), ("AMBERVANE FLORIST", "florist", "listing_full_name"),
    ("KESTRINE CLINIC", "clinic", "uen_on_site"), ("NOLLARD FREIGHT", "freight", "postal_tie"),
    ("RAVELYN STUDIO", "photography", "job_ad"), ("TAMBERLOW CATERING", "catering", "listing_postal"),
    ("ELVANOR TUITION", "tuition", "name_on_site"), ("GLIMMERDALE SPA", "spa", "listing_full_name"),
    ("BRACKWOOD CARPENTRY", "carpentry", "uen_on_site"), ("OSTRIEL MOTORS", "motors", "postal_tie"),
    ("FERNLOWE PRINTING", "printing", "job_ad"), ("CORVALE SECURITY", "security", "listing_postal"),
    ("MIRROWIND LAUNDRY", "laundry", "name_on_site"), ("LARKWEN OPTICAL", "optical", "listing_full_name"),
]


def standard(add, fid, group, name, industry, method, postal, note=""):
    """A firm whose own site is tied to it by one firm-tied signal (`method`)."""
    company = f"{name} PTE. LTD."
    key = name.split()[0].lower()
    d = f"{key}{name.split()[1].lower()[:4]}.sg"
    title = name.title()
    kw = dict(industry=industry, note=note or f"Firm-tied signal: {method.replace('_', ' ')}.")
    other = f"{int(postal) + 500:06d}"
    if method == "job_ad":
        r = add(fid, group, company, "URL from the job ad", d, job_ad_url=f"https://{d}", acra_postal=postal, **kw)
        text = f"{title}. {industry} services in Singapore."
    elif method == "listing_postal":
        r = add(fid, group, company, "listing postal code + name tie", d, address=f"{postal[-2:]} MOCK STREET {postal}",
                maps=[M(title, f"{postal[-2:]} Mock St, Singapore {postal}", f"https://{d}")], **kw)
        text = f"{title}. {industry} in Singapore."
    elif method == "name_on_site":
        r = add(fid, group, company, "registered name on site", d, acra_postal=postal,
                maps=[M(title, f"1 Branch Rd, Singapore {other}", f"https://{d}")], **kw)
        text = f"{industry} in Singapore. (c) 2026 {title} Pte. Ltd."
    elif method == "listing_full_name":
        r = add(fid, group, company, "listing carries the full registered name", d, acra_postal=postal,
                maps=[M(f"{title} Pte Ltd", f"1 Branch Rd, Singapore {other}", f"https://{d}")], **kw)
        text = f"{title}. {industry} in Singapore."
    elif method == "uen_on_site":
        r = add(fid, group, company, "UEN on site", d, acra_postal=postal,
                maps=[M(title, f"1 Branch Rd, Singapore {other}", f"https://{d}")], **kw)
        text = f"{title}. {industry} in Singapore. UEN {r['uen']}."
    elif method == "postal_tie":
        r = add(fid, group, company, "registry postal code on site + name match", d, acra_postal=postal,
                maps=[M(title, f"1 Branch Rd, Singapore {other}", f"https://{d}")], **kw)
        text = f"{title}. {industry}. Head office: 5 Mock Park, Singapore {postal}."
    else:
        raise ValueError(method)
    page(d, title, text)
    return r


for i, (name, ind, method) in enumerate(RANDOM, start=3):
    standard(D, f"R{i:02d}", "random", name, ind, method, f"97{i:02d}00")

# =====================================================================================
# DEV: 10 rows the old step left blank (8 really have no site, 2 do)
# =====================================================================================
D("B01", "blank", "PREMIER IRONWOOD RESOURCES", "missed site, found by search (UEN on site)", "premierironwood.sg",
  industry="timber", acra_postal="980001",
  maps=[M("Premier Ironwood Resources", "1 Timber Rd, Singapore 980001")],
  google=[G("Premier Ironwood | Timber supply", "https://premierironwood.sg")])
page("premierironwood.sg", "Premier Ironwood", f"Timber and plywood supply. Premier Ironwood Resources (UEN {dev[-1]['uen']}). Singapore.")

D("B02", "blank", "PERIWYNKLE SINGAPORE PTE. LTD.", "missed site, name-only evidence", "periwynkle.asia",
  industry="retail", acra_postal="980002",
  maps=[M("Periwynkle", "2 Shop Rd, Singapore 980002")],
  google=[G("Periwynkle | Handmade jewellery", "https://periwynkle.asia")],
  note="Phone on the site matches the listing.")
page("periwynkle.asia", "Periwynkle | Handmade jewellery", "Handmade jewellery, ships from Singapore.")

BLANKS = [  # no own website; some searches return lookalikes the judge should reject
    ("B03", "PSALTER FAMILY CLINIC PTE. LTD.", "clinic", [G("Psalter Family Clinic - ClinicFinder", "https://clinicfinder.sg/psalter"),
                                                         G("Psalter Family Clinic | ClinicBookr", "https://clinicbookr.sg/psalter")]),
    ("B04", "FENGWEI PTE. LTD.", "restaurant", [G("Fengwei Palace | Casino resort dining", "https://fengweipalace.com.sg")]),
    ("B05", "LUMEWAY CITY OF STARS PTE. LTD.", "hotpot", []),
    ("B06", "KORRIN CLEAN PTE. LTD.", "cleaning", [G("Korrin Cleaning Marketplace", "https://korrinclean.com"),
                                                  G("Korrin Clean | SGFirmList", "https://sgfirmlist.com/korrin-clean")]),
    ("B07", "VANTRO TECH PTE. LTD.", "software", [G("Vantro Tech jobs - JobBeeq", "https://jobbeeq.com/company/vantro")]),
    ("B08", "SELWYTH MART", "grocery", [G("Selwyth Mart | BizDirSG", "https://bizdirsg.com/selwyth-mart")]),
    ("B09", "OKARRA HOUSE PTE. LTD.", "food", []),
    ("B10", "TIMBREL STUDIO", "music", [G("Timbrel Music Academy (Melbourne)", "https://timbrelacademymel.com.au")]),
]
for fid, company, ind, google in BLANKS:
    D(fid, "blank", company, "no own website", None, industry=ind, acra_postal=f"98{fid[1:]:0>2}00",
      maps=[M(company.title().replace(" Pte. Ltd.", ""), f"1 Mock Rd, Singapore 98{fid[1:]:0>2}00")], google=google,
      note="Google listing / directories only (checked by hand).")
page("clinicbookr.sg", "Psalter Family Clinic | ClinicBookr", "Book online with clinics across Singapore. Compare 200 GPs. Directory.")
page("fengweipalace.com.sg", "Fengwei Palace", "Casino resort dining in Singapore.")
page("korrinclean.com", "Korrin Cleaning Marketplace", "Cleaning marketplace in Singapore. Compare 300 cleaners.")
page("timbrelacademymel.com.au", "Timbrel Music Academy", "Music lessons in Melbourne, Australia.")

# =====================================================================================
# HOLDOUT: 25 fresh firms, run once, no tuning afterwards
# =====================================================================================
HOLD_RIGHT = [
    ("ARNVALE PHYSIO", "physio", "job_ad"), ("BELLWICK AIRCON", "aircon", "listing_postal"),
    ("CASSOWAY TUITION", "tuition", "name_on_site"), ("DORREL ENGINEERING", "engineering", "listing_full_name"),
    ("EMBERLYN BAKERY", "bakery", "uen_on_site"), ("FAIRHOLT MOVERS", "movers", "postal_tie"),
    ("GALLOWYN SKIN", "skincare", "job_ad"), ("HAVERMILL TRADING", "trading", "listing_postal"),
    ("ISTRAVE INTERIOR", "interior", "name_on_site"), ("JESSAMY FLORIST", "florist", "listing_full_name"),
    ("KILNMORE CERAMICS", "ceramics", "uen_on_site"), ("LOVRELL MARINE", "marine", "postal_tie"),
    ("MERRIVANE CLINIC", "clinic", "listing_postal"), ("NETHERBY LOGISTICS", "logistics", "job_ad"),
    ("OAKVANE PRINTING", "printing", "name_on_site"),
]
for i, (name, ind, method) in enumerate(HOLD_RIGHT, start=1):
    standard(H, f"H{i:02d}", "holdout", name, ind, method, f"99{i:02d}00")

# Sister companies sharing a registered office and one website: both right (dedupe is a later step).
for fid, company in (("H16", "CORVANE HOLDINGS PTE. LTD."), ("H17", "CORVANE SERVICES PTE. LTD.")):
    H(fid, "holdout", company, "sister companies, one shared website", "corvane.sg", industry="facilities",
      acra_postal="991600", maps=[M("Corvane", "16 Mock Park, Singapore 993600", "https://corvane.sg")],
      note="Group site lists both companies.")
page("corvane.sg", "Corvane", "Facilities management in Singapore. Corvane Holdings Pte. Ltd. and Corvane Services Pte. Ltd.")

# Correctly blank: marketplace / directory only.
H("H18", "holdout", "PELLARD CLEANING PTE. LTD.", "no own website (marketplace ranks first)", None, industry="cleaning",
  acra_postal="991800", maps=[M("Helpnest - Pellard Cleaning", "Somewhere Rd, Singapore 912345", "https://helpnest.com.sg")])
H("H19", "holdout", "QUENBY BEAUTY PTE. LTD.", "no own website", None, industry="beauty", acra_postal="991900",
  maps=[M("Quenby Beauty", "19 Mock Rd, Singapore 991900")], google=[G("Quenby Beauty | BizDirSG", "https://bizdirsg.com/quenby")])

# Ambiguous: two firm-tied candidates (subsidiary vs parent, two outlets); a person picks.
for fid, name, truth, other in (("H20", "ROSSVANE DENTAL", "rossvanedental.sg", "rossvanegroup.com"),
                                ("H21", "STARWICK KIDS", "starwickkids.sg", "starwickkidsclub.com"),
                                ("H22", "TOLLVANE FITNESS", "tollvanefit.sg", "tollvanegroup.com")):
    postal = f"99{fid[1:]}00"
    H(fid, "holdout", f"{name} PTE. LTD.", "two firm-tied candidates (parent vs own)", truth, industry="services",
      address=f"{fid[1:]} MOCK TOWER {postal}",
      maps=[M(f"{name.title()} Group", f"{fid[1:]} Mock Tower, Singapore {postal}", f"https://{other}"),
            M(name.title(), f"{fid[1:]} Mock Tower, #05-01, Singapore {postal}", f"https://{truth}")],
      note=f"Own site {truth}; {other} is the parent / sister brand.")
    page(truth, name.title(), f"{name.title()} in Singapore.")
    page(other, f"{name.title()} Group", f"{name.title()} Group of companies, Singapore.")

# Missed: real site with name-only evidence.
H("H23", "holdout", "UMBERVALE TEA PTE. LTD.", "missed site, name-only evidence", "umbervale.co", industry="tea",
  acra_postal="992300", maps=[M("Umbervale Tea", "23 Mock Rd, Singapore 992300")],
  google=[G("Umbervale | Loose-leaf tea", "https://umbervale.co")])
page("umbervale.co", "Umbervale | Loose-leaf tea", "Loose-leaf tea blends, Singapore.")

# Unsure labels (not scored).
H("H24", "holdout", "VESTREL PARTNERS PTE. LTD.", "label unsure", "unsure", industry="consulting",
  acra_postal="992400", maps=[M("Vestrel Partners", "1 Branch Rd, Singapore 992900", "https://vestrelpartners.com")],
  note="Site shows the name but no address or UEN; could be a namesake abroad.")
page("vestrelpartners.com", "Vestrel Partners", "Vestrel Partners Pte. Ltd. Advisory. Offices in Singapore and London.")
H("H25", "holdout", "WYNDCLIFFE ARTS", "label unsure", "unsure", industry="art",
  acra_postal="992500", job_ad_url="https://wyndcliffe.art")
page("wyndcliffe.art", "Wyndcliffe", "Art classes in Singapore.")

# =====================================================================================
for name, rows in (("dev_firms.jsonl", dev), ("holdout_firms.jsonl", hold)):
    (HERE / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
(HERE / "pages.json").write_text(json.dumps({"_note": "SYNTHETIC page excerpts; a missing domain = site did not load.",
                                             **dict(sorted(pages.items()))}, indent=1, ensure_ascii=False))
for name, rows in (("dev_labels.csv", labels_dev), ("holdout_labels.csv", labels_hold)):
    with (HERE / "labels" / name).open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
print(f"dev {len(dev)} firms, holdout {len(hold)} firms, {len(pages)} pages")
