"""Recommendation logic module

This module contains a single, focused function `compute_recommendation_logic`
that implements the recommendation algorithm originally embedded in the
Dash app. It intentionally avoids any Dash, HTML or UI dependencies and
returns a plain structured dictionary suitable for unit tests, CLI use, or
importing from other scripts.

It will try to load the local `LVM_Risk_Database.csv` from `./data` by default
so the function can be used directly without passing the full dataset.
If you prefer to pass the adat dataframe explicitly, provide it to the
`adat_df` parameter.
"""
from typing import Optional, Dict, Any, List
import os
import pandas as pd

"""DATA_DIR = os.getenv("DATA_DIR", "./data")"""


def _load_adat_data() -> pd.DataFrame:
    """Load LVM_Risk_Database table.

    Priority order:
      1. If `app.toolresults` is importable, call its `load_all_csvs()` (or
         use an exported `datasets` dict) and return the `LVM_Risk_Database.csv`
         dataframe from that dict.
      2. Fall back to reading `./data/LVM_Risk_Database.csv` from disk.
    """
    # Try to get the datasets from the toolresults module (Supabase loader)
    try:
        # prefer package import when running as module, fall back to top-level
        try:
            from app import dataRoute as _tr
        except Exception:
            import app.dataRoute as _tr

        datasets = {}
        if hasattr(_tr, "load_all_csvs"):
            try:
                datasets = _tr.load_all_csvs() or {}
            except Exception:
                datasets = getattr(_tr, "datasets", {}) or {}
        else:
            datasets = getattr(_tr, "datasets", {}) or {}

        # Common key in toolresults is the filename
        for key in ("LVM_Risk_Database.csv", "LVM_Risk_Database"):
            if key in datasets:
                df = datasets[key]
                if isinstance(df, pd.DataFrame):
                    return df
                else:
                    return pd.DataFrame(df)
    except Exception:
        # importing toolresults failed; fall back to disk
        pass


def compute_recommendation_logic(
    a30: int,
    a50: int,
    a70: int,
    bgid: Optional[str],
    proj_size: int,
    adat_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Compute recommendation for a proposed project.

        Inputs:
            - a30, a50, a70: counts of units reserved at the given AMI levels
      - bgid: GISJOIN or identifier used to select the row in adat_df
      - proj_size: total number of units in the project
      - adat_df: optional dataframe containing area indicators (if None,
        the function will attempt to load `./data/LVM_Risk_Database.csv`)

    Returns a dict with keys: success (bool), recommendation (str),
    messages (list), and diagnostic values used in the decision.
    """
    # Basic validation
    # Only three affordability levels are used: 30%, 50%, and 70% AMI
    inputs = [a30, a50, a70]
    if any(v is None or v < 0 for v in inputs):
        return {"success": False, "error": "All affordability inputs must be non-negative integers."}
    if proj_size is None or proj_size <= 0:
        return {"success": False, "error": "proj_size must be a positive integer."}

    if adat_df is None:
        adat_df = _load_adat_data()

    # Accept multiple adat_df shapes: dict (toolresults-style), list of records, or DataFrame
    # Normalize into a pandas DataFrame so downstream code can use .empty and column access.
    if isinstance(adat_df, dict):
        # toolresults returns a dict keyed by filenames like 'LVM_Risk_Database' or 'LVM_Risk_Database.csv'
        for key in ("LVM_Risk_Database", "LVM_Risk_Database.csv"):
            if key in adat_df:
                val = adat_df[key]
                adat_df = val if isinstance(val, pd.DataFrame) else pd.DataFrame(val)
                break
        else:
            # Try to coerce the dict into a DataFrame (may produce a 1-row df if mapping is a record)
            try:
                adat_df = pd.DataFrame(adat_df)
            except Exception:
                adat_df = pd.DataFrame()

    elif isinstance(adat_df, list):
        try:
            adat_df = pd.DataFrame(adat_df)
        except Exception:
            adat_df = pd.DataFrame()

    if bgid is None:
        return {"success": False, "error": "bgid (area id) is required."}

    if adat_df.empty:
        return {"success": False, "error": "adat data not available (LVM_Risk_Database.csv missing or empty)."}

    fmi = adat_df[adat_df.get("GISJOIN_proj") == bgid]
    if fmi.empty:
        return {"success": False, "error": "No area data available for the selected location.", "bgid": bgid}
    fmi = fmi.iloc[0]

    # Helpers
    def pct_or_zero(num, denom):
        try:
            return round(float(num) / float(denom) * 100, 0)
        except Exception:
            return 0
        

    # Extract indicators used by the logic
    all_renters_ct = fmi.get("all_renters_ct", 1) or 1
    aff_pct_list = [
        pct_or_zero(fmi.get("renters30_ct", 0), all_renters_ct),
        pct_or_zero(fmi.get("renters50_ct", 0), all_renters_ct),
        pct_or_zero(fmi.get("renters70_ct", 0), all_renters_ct),
    ]

    aff_proj_cumulative = [
        a30,
        a30 + a50,
        a30 + a50 + a70,
    ]

    aff_levels = ["30% AMI", "50% AMI", "70% AMI"]

    aff_df = pd.DataFrame({
        "aff_level": aff_levels,
        "aff_pct": aff_pct_list,
        "aff_proj": aff_proj_cumulative,
    })

    # Determine the crit2 index (first aff level covering >50% of renters)
    idx_over50 = aff_df[aff_df["aff_pct"] > 50]
    crit2_index = int(idx_over50.index[0]) if not idx_over50.empty else None

    crit3_cost_burden = fmi.get("cost_burden30_20_p", 0) or 0
    cost_burden_pct = round(float(crit3_cost_burden) * 100, 0) if crit3_cost_burden else 0

    risk_level = fmi.get("risk_level", "unknown")

    messages: List[str] = []
    recommendation = "undetermined"

    # Safety: project-wide affordability check
    # Only the total number of affordable units (not the cumulative sum) must not exceed project size.
    total_affordable_units = a30 + a50 + a70
    if total_affordable_units > proj_size:
        return {"success": False, "error": "Total affordable units cannot exceed project size."}

    # Compute share_affordable_at_crit2 (if applicable)
    if crit2_index is not None and proj_size:
        share_affordable_at_crit2 = round(aff_df.loc[crit2_index, "aff_proj"] / proj_size * 100, 0)
    else:
        share_affordable_at_crit2 = 0

    # Decision logic (kept as close as possible to the original)
    if risk_level == "high":
        # "All units affordable" now means all units are affordable at or below 70% AMI
        meets_all_affordable = (aff_df.loc[2, "aff_proj"] == proj_size)
        if meets_all_affordable:
            messages.append("The project meets the requirement that all units be affordable.")
            recommendation = "recommended"
        else:
            messages.append("Projects in high-risk areas are required to only include affordable units.")

        if crit2_index is not None:
            messages.append(f"{share_affordable_at_crit2}% of units are affordable at {aff_df.loc[crit2_index, 'aff_level']}.")
            meets_burden_condition = share_affordable_at_crit2 >= cost_burden_pct
            if meets_burden_condition:
                messages.append("The project meets the requirement that the share of units affordable to at least half the renter population be >= the percent of housing cost-burdened households.")
                if meets_all_affordable:
                    recommendation = "recommended"
                else:
                    # qualifies on burden but not fully affordable
                    recommendation = "conditional"
            else:
                messages.append(f"The share of units affordable to at least half the renter population must be >= {cost_burden_pct}% (current: {share_affordable_at_crit2}%).")
                recommendation = "not_recommended"
        else:
            messages.append("No affordability level covers a majority (>50%) of renters in this area.")
            recommendation = "not_recommended"

    elif risk_level == "medium":
        if share_affordable_at_crit2 >= cost_burden_pct and crit2_index is not None:
            messages.append(f"{share_affordable_at_crit2}% of units are affordable at {aff_df.loc[crit2_index,'aff_level']}. This project meets the requirement and is recommended for support.")
            recommendation = "recommended"
        else:
            messages.append(f"{share_affordable_at_crit2}% of units are affordable at {aff_df.loc[crit2_index,'aff_level'] if crit2_index is not None else 'N/A'}. The share of units affordable to at least half the renter population must be >= {cost_burden_pct}% of housing cost-burdened households.")
            recommendation = "not_recommended"

    else:  # low risk or unknown
        # share of units affordable at 50% AMI or below
        share_50_or_below = (aff_df.loc[1, "aff_proj"] / proj_size) if proj_size else 0
        if share_50_or_below >= 0.1:
            messages.append(f"{round(share_50_or_below * 100,0)}% of units are affordable at 50% AMI or below. This project is recommended for support.")
            recommendation = "recommended"
        else:
            messages.append("Projects in low risk areas must include at least 10% of units affordable at 50% AMI or below.")
            recommendation = "not_recommended"

    # Return structured result
    return {
        "success": True,
        "recommendation": recommendation,
        "messages": messages,
        "risk_level": risk_level,
        "crit2_index": crit2_index,
        "share_affordable_at_crit2": share_affordable_at_crit2,
        "cost_burden_pct": cost_burden_pct,
        "aff_df": aff_df.to_dict(orient="list"),
    }


if __name__ == "__main__":
    # Simple CLI demo using a sample bgid if the data exists.
    import argparse

    parser = argparse.ArgumentParser(description="Compute recommendation for a sample project.")
    parser.add_argument("bgid", help="GISJOIN_proj value for the area (bgid)")
    parser.add_argument("proj_size", type=int, help="Total number of units in project")
    parser.add_argument("--a30", type=int, default=0, help="Units at 30% AMI")
    parser.add_argument("--a50", type=int, default=0, help="Units at 50% AMI")
    parser.add_argument("--a70", type=int, default=0, help="Units at 70% AMI")
    args = parser.parse_args()

    adat = _load_adat_data()
    out = compute_recommendation_logic(args.a30, args.a50, args.a70, args.bgid, args.proj_size, adat_df=adat)
    print(out)
