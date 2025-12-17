import pytest
import logging
import pandas as pd

from app.app import compute_recommendation_logic


def make_fmi_record(gisjoin, renters30, renters50, renters70, cost_burden_p, risk_level):
    return {
        "GISJOIN_proj": gisjoin,
        "all_renters_ct": renters30 + renters50 + renters70,
        "renters30_ct": renters30,
        "renters50_ct": renters50,
        "renters70_ct": renters70,
        "cost_burden30_20_p": cost_burden_p,
        "risk_level": risk_level,
    }


def test_compute_recommendation_high_risk_all_affordable_with_dict():
    # High risk area; all units affordable at 70% AMI -> recommended
    rec = make_fmi_record("bg1", renters30=10, renters50=10, renters70=80, cost_burden_p=0.2, risk_level="high")
    adat = {"LVM_Risk_Database": [rec]}

    out = compute_recommendation_logic(a30=0, a50=0, a70=10, bgid="bg1", proj_size=10, adat_df=adat)
    logging.getLogger(__name__).info("test_compute_recommendation_high_risk_all_affordable_with_dict output: %s", out)
    assert out["success"] is True
    assert out["recommendation"] == "recommended"


def test_compute_recommendation_medium_not_recommended():
    # Medium risk; affordability share below cost burden -> not_recommended
    rec = make_fmi_record("bg2", renters30=10, renters50=10, renters70=30, cost_burden_p=0.6, risk_level="medium")
    # provide as list (toolresults-like)
    out = compute_recommendation_logic(a30=1, a50=1, a70=1, bgid="bg2", proj_size=10, adat_df=[rec])
    logging.getLogger(__name__).info("test_compute_recommendation_medium_not_recommended output: %s", out)
    assert out["success"] is True
    assert out["recommendation"] == "not_recommended"


def test_compute_recommendation_low_recommended_by_50pct_share():
    # Low risk; ensure 50% AMI share >= 10% -> recommended
    rec = make_fmi_record("bg3", renters30=5, renters50=20, renters70=5, cost_burden_p=0.1, risk_level="low")
    adat_df = pd.DataFrame([rec])
    out = compute_recommendation_logic(a30=0, a50=2, a70=0, bgid="bg3", proj_size=10, adat_df=adat_df)
    logging.getLogger(__name__).info("test_compute_recommendation_low_recommended_by_50pct_share output: %s", out)
    assert out["success"] is True
    assert out["recommendation"] == "recommended"


def test_invalid_aff_inputs_negative():
    # Negative affordability input should return an error
    rec = make_fmi_record("bg4", renters30=1, renters50=1, renters70=1, cost_burden_p=0.1, risk_level="low")
    out = compute_recommendation_logic(a30=-1, a50=0, a70=0, bgid="bg4", proj_size=10, adat_df=[rec])
    logging.getLogger(__name__).info("test_invalid_aff_inputs_negative output: %s", out)
    assert out.get("success") is False
    assert "non-negative" in out.get("error", "")


def test_proj_size_zero():
    # proj_size must be positive
    rec = make_fmi_record("bg5", renters30=1, renters50=1, renters70=1, cost_burden_p=0.1, risk_level="low")
    out = compute_recommendation_logic(a30=0, a50=0, a70=0, bgid="bg5", proj_size=0, adat_df=[rec])
    logging.getLogger(__name__).info("test_proj_size_zero output: %s", out)
    assert out.get("success") is False
    assert "proj_size must be a positive integer" in out.get("error", "")


def test_bgid_not_found():
    # bgid not present in adat_df should return a helpful error
    rec = make_fmi_record("bg6", renters30=5, renters50=5, renters70=0, cost_burden_p=0.1, risk_level="low")
    out = compute_recommendation_logic(a30=0, a50=0, a70=0, bgid="no-such", proj_size=10, adat_df=[rec])
    logging.getLogger(__name__).info("test_bgid_not_found output: %s", out)
    assert out.get("success") is False
    assert out.get("bgid") == "no-such"


def test_total_aff_exceeds_proj_size():
    # Sum of aff units cannot exceed project size
    rec = make_fmi_record("bg7", renters30=10, renters50=0, renters70=0, cost_burden_p=0.1, risk_level="low")
    out = compute_recommendation_logic(a30=5, a50=5, a70=5, bgid="bg7", proj_size=10, adat_df=[rec])
    logging.getLogger(__name__).info("test_total_aff_exceeds_proj_size output: %s", out)
    assert out.get("success") is False
    assert "Total affordable units cannot exceed project size" in out.get("error", "")


def test_high_risk_conditional():
    # High risk where share meets burden but not all units affordable -> conditional
    rec = make_fmi_record("bg8", renters30=60, renters50=30, renters70=10, cost_burden_p=0.5, risk_level="high")
    out = compute_recommendation_logic(a30=6, a50=2, a70=0, bgid="bg8", proj_size=10, adat_df=[rec])
    logging.getLogger(__name__).info("test_high_risk_conditional output: %s", out)
    assert out.get("success") is True
    assert out.get("recommendation") == "conditional"


def test_low_not_recommended():
    # Low risk but insufficient share at 50% AMI or below -> not_recommended
    rec = make_fmi_record("bg9", renters30=1, renters50=1, renters70=8, cost_burden_p=0.1, risk_level="low")
    out = compute_recommendation_logic(a30=0, a50=0, a70=0, bgid="bg9", proj_size=10, adat_df=[rec])
    logging.getLogger(__name__).info("test_low_not_recommended output: %s", out)
    assert out.get("success") is True
    assert out.get("recommendation") == "not_recommended"
