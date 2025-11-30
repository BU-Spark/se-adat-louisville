from typing import Optional, Dict, Any, List
import os
import pandas as pd


def _load_adat_data() -> pd.DataFrame:
    """Load LVM_Risk_Database table.

    Priority order:
      1. If `toolresults` module is available, use its load_all_csvs()
      2. Fall back to reading `./data/LVM_Risk_Database.csv` from disk
    """
    try:
        try:
            from app import toolresults as _tr
        except Exception:
            import toolresults as _tr

        datasets = {}
        if hasattr(_tr, "load_all_csvs"):
            try:
                datasets = _tr.load_all_csvs() or {}
            except Exception:
                datasets = getattr(_tr, "datasets", {}) or {}
        else:
            datasets = getattr(_tr, "datasets", {}) or {}

        for key in ("LVM_Risk_Database.csv", "LVM_Risk_Database"):
            if key in datasets:
                df = datasets[key]
                if isinstance(df, pd.DataFrame):
                    return df
                else:
                    return pd.DataFrame(df)
    except Exception:
        pass
    
    # Fall back to local file
    try:
        return pd.read_csv("./data/LVM_Risk_Database.csv")
    except Exception:
        return pd.DataFrame()


def find_sector_row(adat_df: pd.DataFrame, bgid: str) -> Optional[pd.Series]:
    """
    Robustly find the sector/area row in the database.
    
    Tries multiple identifier column names and matching strategies:
    1. GISJOIN_proj (primary)
    2. GISJOIN (fallback)
    3. bgid (if exists)
    4. GEOID (if exists)
    
    Also handles type mismatches by trying string conversion.
    Handles GISJOIN values with/without leading 'G'.
    
    Args:
        adat_df: DataFrame with area risk data
        bgid: Geographic identifier to search for
    
    Returns:
        pandas Series with the matching row, or None if not found
    """
    if adat_df.empty or bgid is None:
        return None
    
    # List of potential identifier columns to try, in priority order
    id_columns = ["GISJOIN_proj", "GISJOIN", "bgid", "GEOID"]
    
    # Also try any column with 'gis' or 'join' in the name
    extra_cols = [col for col in adat_df.columns if any(
        keyword in col.lower() for keyword in ['gis', 'join']
    ) and col not in id_columns]
    id_columns.extend(extra_cols)
    
    for col in id_columns:
        if col not in adat_df.columns:
            continue
        
        # Try exact match
        matches = adat_df[adat_df[col] == bgid]
        if not matches.empty:
            return matches.iloc[0]
        
        # Try string conversion (handles int vs string mismatches)
        try:
            matches = adat_df[adat_df[col].astype(str) == str(bgid)]
            if not matches.empty:
                return matches.iloc[0]
        except (TypeError, ValueError):
            pass
        
        # For GISJOIN-style columns, also try toggling a leading 'G'
        if col.lower().startswith("gisjoin"):
            try:
                bgid_str = str(bgid)
                alt = bgid_str[1:] if bgid_str.startswith("G") else f"G{bgid_str}"
                matches = adat_df[adat_df[col].astype(str) == alt]
                if not matches.empty:
                    return matches.iloc[0]
            except (TypeError, ValueError):
                pass
    
    return None


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
    inputs = [a30, a50, a70]
    if any(v is None or v < 0 for v in inputs):
        return {
            "success": False, 
            "error": "All affordability inputs must be non-negative integers."
        }
    if proj_size is None or proj_size <= 0:
        return {
            "success": False, 
            "error": "proj_size must be a positive integer."
        }

    if bgid is None:
        return {
            "success": False, 
            "error": "bgid (area id) is required."
        }

    # Load data if not provided
    if adat_df is None:
        adat_df = _load_adat_data()

    # Normalize adat_df to DataFrame
    if isinstance(adat_df, dict):
        for key in ("LVM_Risk_Database", "LVM_Risk_Database.csv"):
            if key in adat_df:
                val = adat_df[key]
                adat_df = val if isinstance(val, pd.DataFrame) else pd.DataFrame(val)
                break
        else:
            try:
                adat_df = pd.DataFrame(adat_df)
            except Exception:
                adat_df = pd.DataFrame()
    elif isinstance(adat_df, list):
        try:
            adat_df = pd.DataFrame(adat_df)
        except Exception:
            adat_df = pd.DataFrame()

    if adat_df.empty:
        return {
            "success": False, 
            "error": "adat data not available (LVM_Risk_Database.csv missing or empty)."
        }

    # Use robust sector lookup
    fmi = find_sector_row(adat_df, bgid)
    
    if fmi is None:
        # Provide helpful diagnostic info
        available_ids = [col for col in adat_df.columns if any(
            keyword in col.lower() for keyword in ['gis', 'join', 'bgid', 'geoid']
        )]
        return {
            "success": False,
            "error": f"No area data found for bgid='{bgid}'.",
            "bgid": bgid,
            "available_identifier_columns": available_ids,
            "sample_identifiers": adat_df[available_ids[0]].head(5).tolist() if available_ids else [],
            "hint": "Check if bgid value matches the format in the database. Run diagnose_sector.py for detailed analysis."
        }

    # Helper function
    def pct_or_zero(num, denom):
        try:
            return round(float(num) / float(denom) * 100, 0)
        except Exception:
            return 0

    # Extract indicators
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

    # Validation: total affordable units
    total_affordable_units = a30 + a50 + a70
    if total_affordable_units > proj_size:
        return {
            "success": False, 
            "error": "Total affordable units cannot exceed project size."
        }

    # Compute share_affordable_at_crit2
    if crit2_index is not None and proj_size:
        share_affordable_at_crit2 = round(
            aff_df.loc[crit2_index, "aff_proj"] / proj_size * 100, 0
        )
    else:
        share_affordable_at_crit2 = 0

    # Decision logic by risk level
    if risk_level == "high":
        # All units must be affordable at or below 70% AMI
        meets_all_affordable = (aff_df.loc[2, "aff_proj"] == proj_size)
        
        if meets_all_affordable:
            messages.append("✓ The project meets the requirement that all units be affordable.")
            recommendation = "recommended"
        else:
            messages.append("✗ Projects in high-risk areas are required to only include affordable units.")

        if crit2_index is not None:
            messages.append(
                f"{share_affordable_at_crit2}% of units are affordable at "
                f"{aff_df.loc[crit2_index, 'aff_level']}."
            )
            meets_burden_condition = share_affordable_at_crit2 >= cost_burden_pct
            
            if meets_burden_condition:
                messages.append(
                    f"✓ The project meets the requirement that the share of units affordable "
                    f"to at least half the renter population be >= {cost_burden_pct}% "
                    f"(housing cost-burdened households)."
                )
                if meets_all_affordable:
                    recommendation = "recommended"
                else:
                    recommendation = "conditional"
            else:
                messages.append(
                    f"✗ The share of units affordable to at least half the renter population "
                    f"must be >= {cost_burden_pct}% (current: {share_affordable_at_crit2}%)."
                )
                recommendation = "not_recommended"
        else:
            messages.append("✗ No affordability level covers a majority (>50%) of renters in this area.")
            recommendation = "not_recommended"

    elif risk_level == "medium":
        if share_affordable_at_crit2 >= cost_burden_pct and crit2_index is not None:
            messages.append(
                f"✓ {share_affordable_at_crit2}% of units are affordable at "
                f"{aff_df.loc[crit2_index,'aff_level']}. This project meets the requirement "
                f"and is recommended for support."
            )
            recommendation = "recommended"
        else:
            ami_level = aff_df.loc[crit2_index,'aff_level'] if crit2_index is not None else 'N/A'
            messages.append(
                f"✗ {share_affordable_at_crit2}% of units are affordable at {ami_level}. "
                f"The share must be >= {cost_burden_pct}% of housing cost-burdened households."
            )
            recommendation = "not_recommended"

    else:  # low risk or unknown
        # Share of units affordable at 50% AMI or below
        share_50_or_below = (aff_df.loc[1, "aff_proj"] / proj_size) if proj_size else 0
        
        if share_50_or_below >= 0.1:
            messages.append(
                f"✓ {round(share_50_or_below * 100, 0)}% of units are affordable at "
                f"50% AMI or below. This project is recommended for support."
            )
            recommendation = "recommended"
        else:
            messages.append(
                "✗ Projects in low risk areas must include at least 10% of units "
                "affordable at 50% AMI or below."
            )
            recommendation = "not_recommended"

    # Return structured result
    return {
        "success": True,
        "recommendation": recommendation,
        "messages": messages,
        "risk_level": risk_level,
        "bgid": bgid,
        "crit2_index": crit2_index,
        "share_affordable_at_crit2": share_affordable_at_crit2,
        "cost_burden_pct": cost_burden_pct,
        "aff_df": aff_df.to_dict(orient="list"),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compute recommendation for a project.")
    parser.add_argument("bgid", help="GISJOIN_proj value for the area (bgid)")
    parser.add_argument("proj_size", type=int, help="Total number of units in project")
    parser.add_argument("--a30", type=int, default=0, help="Units at 30% AMI")
    parser.add_argument("--a50", type=int, default=0, help="Units at 50% AMI")
    parser.add_argument("--a70", type=int, default=0, help="Units at 70% AMI")
    args = parser.parse_args()

    adat = _load_adat_data()
    out = compute_recommendation_logic(
        args.a30, args.a50, args.a70, 
        args.bgid, args.proj_size, 
        adat_df=adat
    )
    
    print("\n" + "="*80)
    print("RECOMMENDATION RESULT")
    print("="*80)
    
    if out["success"]:
        print(f"\n✓ Success: {out['recommendation'].upper()}")
        print(f"Risk Level: {out['risk_level']}")
        print(f"\nDetails:")
        for msg in out["messages"]:
            print(f"  {msg}")
    else:
        print(f"\n✗ Error: {out['error']}")
        if "hint" in out:
            print(f"\n💡 Hint: {out['hint']}")
