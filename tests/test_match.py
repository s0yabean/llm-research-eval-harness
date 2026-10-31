"""Tests for the matchers and the eval itself.

The synthetic rows have known answers, so these test the *code*, not the pipeline's accuracy.

    python -m pytest tests/ -q
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import judges  # noqa: E402
import run_eval  # noqa: E402
from match import dom, evidence_match, is_directory, naive_match, rule_check  # noqa: E402

DEV, HOLD = run_eval.load("dev"), run_eval.load("holdout")
PAGES = run_eval.PAGES
BY_ID = {f["id"]: f for f in DEV + HOLD}


def test_dom():
    assert dom("https://www.Example.com.sg/contact?x=1") == "example.com.sg"
    assert dom("none") is None and dom("") is None


def test_directories_are_never_the_website():
    assert is_directory("helpnest.com.sg") and is_directory("facebook.com")
    assert not is_directory("brightmossreno.sg")


@pytest.mark.parametrize("fid", ["D01", "D02", "D03", "D04", "D05", "D06"])
def test_rule_check_catches_unrelated_domains(fid):
    f = BY_ID[fid]
    assert rule_check(f["company"], naive_match(f)["website"]) == "flag"


@pytest.mark.parametrize("fid", ["D07", "D08", "D09", "D11", "R01"])
def test_rule_check_misses_common_word_collisions(fid):
    """Known gap, kept on purpose: one shared common word passes the rule check."""
    f = BY_ID[fid]
    assert rule_check(f["company"], naive_match(f)["website"]) == "pass"


def test_postal_code_alone_is_not_evidence():
    # Mall listing and same-building neighbour share the postal code but not the name.
    for fid in ("D03", "D05"):
        assert evidence_match(BY_ID[fid], PAGES, judges.MockJudge())["website"] is None


def test_listing_name_must_be_the_registered_name():
    # "Doctor Frigo Pte Ltd" (other firm) loses to "Dr. Frigo Asia" at the job-ad postal code.
    assert evidence_match(BY_ID["D13"], PAGES, judges.MockJudge())["website"] == "doctorfrigo.sg"


def test_two_firm_tied_sites_go_to_a_person():
    r = evidence_match(BY_ID["H20"], PAGES, judges.MockJudge())
    assert r["status"] == "ambiguous" and "rossvanedental.sg" in r["alternatives"]


def test_blank_is_a_valid_answer():
    r = evidence_match(BY_ID["B05"], PAGES, judges.MockJudge())
    assert r["website"] is None and r["status"] == "none"


def test_judge_threshold_is_respected():
    r = evidence_match(BY_ID["R02"], PAGES, judges.MockJudge())
    assert r["judged"] and all(j["p"] < 0.85 for j in r["judged"]) and r["website"] is None


def test_dev_set_composition():
    groups = [f["group"] for f in DEV]
    assert (groups.count("flagged"), groups.count("random"), groups.count("blank")) == (20, 30, 10)
    assert sum(f["truth"] == "unsure" for f in HOLD) == 2


def test_before_after_on_synthetic_set():
    before = run_eval.score_dev(DEV, {f["id"]: (naive_match(f)["website"], ()) for f in DEV})
    after = run_eval.score_dev(DEV, {f["id"]: (lambda r: (r["website"], tuple(r["alternatives"])))(
        evidence_match(f, PAGES, judges.MockJudge())) for f in DEV})
    assert (before["wrong"], before["right_outcome"]) == (12, 46)
    assert (after["wrong"], after["right_outcome"]) == (2, 55)


def test_dossier_is_blind():
    entry = run_eval.dossier(BY_ID["D10"])
    blob = json.dumps(entry)
    assert "truth" not in blob and "scenario" not in blob and "pipeline_flagged" not in blob
