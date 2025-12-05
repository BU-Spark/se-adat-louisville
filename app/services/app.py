from typing import Optional, Dict, Any, List, Tuple
import os
import sys
import pandas as pd
import httpx
import logging

logger = logging.getLogger(__name__)

CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/geographies/address"


def _load_adat_data() -> pd.DataFrame:
    """Load LVM_Risk_Database table.

    Priority order:
      1. If `dataLoader` module is available, use its load_all_csvs()
      2. Fall back to reading `./data/LVM_Risk_Database.csv` from disk
    """
    # Add services directory to path so dataLoader can be imported
    services_dir = os.path.join(os.path.dirname(__file__))
    if services_dir not in sys.path:
        sys.path.insert(0, services_dir)
    
    # Try multiple import paths
    import_attempts = [
        ("dataLoader", lambda: __import__("dataLoader")),
        ("app.services.dataLoader", lambda: __import__("app.services.dataLoader", fromlist=["dataLoader"])),
        ("app.dataLoader", lambda: __import__("app.dataLoader", fromlist=["dataLoader"])),
    ]
    
    # Also try direct import if we're in the services directory
    if os.path.basename(os.getcwd()) == "services":
        import_attempts.insert(0, ("dataLoader (direct)", lambda: __import__("dataLoader")))
    
    _tr = None
    for attempt_name, import_func in import_attempts:
        try:
            _tr = import_func()
            print(f"✓ Successfully imported: {attempt_name}")
            break
        except Exception as e:
            print(f"  → Import attempt '{attempt_name}' failed: {e}")
    
    if _tr:
        datasets = {}
        if hasattr(_tr, "load_all_csvs"):
            try:
                datasets = _tr.load_all_csvs() or {}
                print(f"✓ load_all_csvs() returned {len(datasets)} datasets")
            except Exception as e:
                print(f"  → load_all_csvs() failed: {e}")
                datasets = getattr(_tr, "datasets", {}) or {}
        else:
            datasets = getattr(_tr, "datasets", {}) or {}
            print(f"✓ Using datasets attribute ({len(datasets)} datasets)")

        for key in ("LVM_Risk_Database.csv", "LVM_Risk_Database"):
            if key in datasets:
                df = datasets[key]
                if isinstance(df, pd.DataFrame):
                    print(f"✓ Found '{key}' in datasets: {df.shape}")
                    return df
                else:
                    try:
                        df = pd.DataFrame(df)
                        print(f"✓ Converted '{key}' to DataFrame: {df.shape}")
                        return df
                    except Exception as e:
                        print(f"  → Failed to convert '{key}': {e}")
        
        print(f"  → LVM_Risk_Database not found. Available keys: {list(datasets.keys())}")
    
    # Fall back to local file
    local_paths = [
        "./data/LVM_Risk_Database.csv",
        "../data/LVM_Risk_Database.csv",
        "../../data/LVM_Risk_Database.csv",
        "data/LVM_Risk_Database.csv",
        "LVM_Risk_Database.csv",
    ]
    
    for path in local_paths:
        try:
            df = pd.read_csv(path)
            print(f"✓ Loaded from file '{path}': {df.shape}")
            return df
        except Exception:
            pass
    
    print(f"✗ All loading methods failed")
    print(f"  Current directory: {os.getcwd()}")
    return pd.DataFrame()



def find_sector_row(
    adat_df: pd.DataFrame,
    bgid: Optional[str],
    return_column: bool = False
) -> Optional[Tuple[pd.Series, Optional[str]]]:
    """
    Robustly find the sector/area row in the database.
    
    Tries multiple identifier column names and matching strategies:
    1. GISJOIN_proj (primary)
    2. GISJOIN (fallback)
    3. bgid (if exists)
    4. GEOID/GEOID_bg (if exists)
    
    Also handles type mismatches by trying string conversion.
    Handles GISJOIN values with/without leading 'G'.
    
    Args:
        adat_df: DataFrame with area risk data
        bgid: Geographic identifier to search for
        return_column: When True, also return the column that matched
    
    Returns:
        pandas Series with the matching row (and optional column), or None if not found
    """
    if adat_df.empty or bgid is None:
        return (None, None) if return_column else None
    
    # List of potential identifier columns to try, in priority order
    id_columns = [
        "GISJOIN_proj",
        "GISJOIN",
        "bgid",
        "GEOID",
        "GEOID_bg",
        "geoid",
        "geoid_bg",
    ]
    
    # Also try any column with relevant keywords
    extra_cols = [
        col for col in adat_df.columns
        if any(keyword in col.lower() for keyword in ['gis', 'join', 'bgid', 'geoid'])
        and col not in id_columns
    ]
    id_columns.extend(extra_cols)
    
    for col in id_columns:
        if col not in adat_df.columns:
            continue
        
        # Try exact match
        matches = adat_df[adat_df[col] == bgid]
        if not matches.empty:
            result = matches.iloc[0]
            return (result, col) if return_column else result
        
        # Try string conversion (handles int vs string mismatches)
        try:
            col_str = adat_df[col].astype(str)
            matches = adat_df[col_str == str(bgid)]
            if not matches.empty:
                result = matches.iloc[0]
                return (result, col) if return_column else result

            # Handle GEOID columns that include a prefix like '1500000US'
            if "geo" in col.lower():
                bgid_str = str(bgid)
                # If the column values look like '1500000US###########', compare on suffix
                if col_str.str.startswith("1500000US").any():
                    suffix_matches = adat_df[col_str.str[-len(bgid_str):] == bgid_str]
                    if not suffix_matches.empty:
                        result = suffix_matches.iloc[0]
                        return (result, col) if return_column else result
        except (TypeError, ValueError):
            pass
        
        # For GISJOIN-style columns, also try toggling a leading 'G'
        if col.lower().startswith("gisjoin"):
            try:
                bgid_str = str(bgid)
                alt = bgid_str[1:] if bgid_str.startswith("G") else f"G{bgid_str}"
                matches = adat_df[adat_df[col].astype(str) == alt]
                if not matches.empty:
                    result = matches.iloc[0]
                    return (result, col) if return_column else result
            except (TypeError, ValueError):
                pass
    
    return (None, None) if return_column else None


def _geoid_to_gisjoin(bg_geoid: Optional[str]) -> Optional[str]:
    """Convert a 12-digit block group GEOID to NHGIS-style GISJOIN."""
    if not bg_geoid:
        return None
    geoid_str = str(bg_geoid).zfill(12)
    return f"G{geoid_str}0"


def _geocode_with_census(
    address: str,
    city: str,
    state: str,
    zip_code: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Geocode an address and return block group identifiers."""
    params = {
        "street": address,
        "city": city,
        "state": state,
        "zip": zip_code or "",
        "benchmark": "Public_AR_Current",
        "vintage": "Current_Current",
        "format": "json",
    }
    try:
        resp = httpx.get(CENSUS_GEOCODER_URL, params=params, timeout=10)
        resp.raise_for_status()
    except Exception as exc:
        print(f"[BGID Resolver] Census geocoder request failed: {exc}")
        return None
    
    try:
        data = resp.json()
    except Exception as exc:
        print(f"[BGID Resolver] Failed to parse geocoder response: {exc}")
        return None
    
    matches = data.get("result", {}).get("addressMatches") or []
    if not matches:
        print("[BGID Resolver] No geocoder matches returned")
        return None
    
    match = matches[0]
    geographies = match.get("geographies") or {}
    
    block_info = None
    for key, value in geographies.items():
        if "Census Blocks" in key and value:
            block_info = value[0]
            break
    
    if not block_info:
        print("[BGID Resolver] No Census block info available in geocoder response")
        return None
    
    block_geoid = str(block_info.get("GEOID", "")).strip()
    block_group_code = str(block_info.get("BLKGRP", "")).strip()
    tract_code = str(block_info.get("TRACT", "")).strip().zfill(6)
    state_fips = str(block_info.get("STATE", "")).strip().zfill(2)
    county_fips = str(block_info.get("COUNTY", "")).strip().zfill(3)
    
    if not block_group_code and block_geoid:
        # First digit of block code corresponds to block group
        block_group_code = block_geoid[11:12]
    block_group_geoid = (
        f"{state_fips}{county_fips}{tract_code}{block_group_code}"
        if block_group_code and state_fips and county_fips and tract_code
        else block_geoid[:12]
    )
    
    return {
        "coordinates": match.get("coordinates") or {},
        "block_geoid": block_geoid,
        "block_group_geoid": block_group_geoid,
        "state_fips": state_fips,
        "county_fips": county_fips,
        "tract_code": tract_code,
        "block_group_code": block_group_code,
    }


def resolve_bgid(
    address: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
    adat_df: Optional[pd.DataFrame] = None
) -> Tuple[Optional[str], Optional[pd.Series], Dict[str, Any]]:
    """
    Resolve BGID from address/city/state/zip information.
    
    Uses the Census geocoder to obtain a block group GEOID, converts that
    to GISJOIN format, and looks up the matching row in the adat_df.
    """
    details: Dict[str, Any] = {
        "method": "census_geocoder",
        "address": address,
        "city": city,
        "state": state,
        "zip": zip_code,
    }
    
    if not (address and city and state):
        details["error"] = "Address, city, and state are required for BGID resolution."
        return None, None, details
    
    if adat_df is None or adat_df.empty:
        details["error"] = "ADAT data unavailable; cannot resolve BGID."
        return None, None, details
    
    geocode = _geocode_with_census(address, city, state, zip_code)
    details["geocode"] = geocode
    
    if not geocode:
        details["error"] = "Geocoding failed or returned no matches."
        return None, None, details
    
    candidates = []
    if geocode.get("block_group_geoid"):
        candidates.append(geocode["block_group_geoid"])
    if geocode.get("block_geoid"):
        candidates.append(str(geocode["block_geoid"])[:12])
    
    gisjoin_candidate = _geoid_to_gisjoin(geocode.get("block_group_geoid"))
    if gisjoin_candidate:
        # Prefer GISJOIN when available
        candidates.insert(0, gisjoin_candidate)
    
    # Deduplicate while preserving order
    seen = set()
    unique_candidates = []
    for cand in candidates:
        if cand and cand not in seen:
            unique_candidates.append(cand)
            seen.add(cand)
    details["candidates_tested"] = unique_candidates
    
    for cand in unique_candidates:
        row, matched_col = find_sector_row(adat_df, cand, return_column=True)
        if row is not None:
            resolved_bgid = row.get("GISJOIN_proj") or row.get(matched_col) or cand
            details.update({
                "matched_column": matched_col,
                "matched_value": cand,
                "resolved_bgid": str(resolved_bgid),
            })
            return str(resolved_bgid), row, details
    
    details["error"] = "No matching bgid found in ADAT data for the geocoded location."
    return None, None, details





def compute_recommendation_logic(
    a30: int,
    a50: int,
    a70: int,
    bgid: Optional[str],
    proj_size: int,
    adat_df: Optional[pd.DataFrame] = None,
    address: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute recommendation for a proposed project.

    Inputs:
        - a30, a50, a70: counts of units reserved at the given AMI levels
        - bgid: GISJOIN or identifier used to select the row in adat_df
                (if None, will attempt to resolve from address/city/state/zip)
        - proj_size: total number of units in the project
        - adat_df: optional dataframe containing area indicators (if None,
          the function will attempt to load `./data/LVM_Risk_Database.csv`)
        - address, city, state, zip_code: location info for bgid resolution

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

    # Load data if not provided (needed for bgid resolution)
    if adat_df is None:
        print("\nAttempting to load LVM_Risk_Database...")
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

    # Resolve sector row/bgid
    resolution_details: Dict[str, Any] = {}
    fmi_row: Optional[pd.Series] = None
    matched_column: Optional[str] = None

    if bgid is not None:
        fmi_row, matched_column = find_sector_row(adat_df, bgid, return_column=True)
        if fmi_row is not None:
            resolution_details = {
                "method": "provided_bgid",
                "matched_column": matched_column,
                "matched_value": bgid,
            }

    if fmi_row is None:
        resolved_bgid, fmi_row, resolution_details = resolve_bgid(
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            adat_df=adat_df
        )
        if resolved_bgid:
            bgid = resolved_bgid


    if fmi_row is None:
        # Provide helpful diagnostic info
        available_ids = [col for col in adat_df.columns if any(
            keyword in col.lower() for keyword in ['gis', 'join', 'bgid', 'geoid']
        )]
        error_response = {
            "success": False,
            "error": f"No area data found for bgid='{bgid}'.",
            "bgid": bgid,
            "available_identifier_columns": available_ids,
            "sample_identifiers": adat_df[available_ids[0]].head(5).tolist() if available_ids else [],
            "hint": "Check if bgid value matches the format in the database.",
        }
        if resolution_details:
            error_response["bgid_resolution"] = resolution_details
        return error_response
    

    fmi = fmi_row

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

    # DEBUG: Display aff_pct_list and idx_over50 for inspection
    debug_file = "adat_debug.log"
    with open(debug_file, "a") as f:
        f.write(f"[DEBUG] aff_pct_list: {aff_pct_list}\n")
        f.write(f"[DEBUG] idx_over50: {idx_over50.index.tolist()}\n")
        f.write(f"[DEBUG] crit2_index: {crit2_index}\n")
        f.write(f"[DEBUG] aff_df:\n{aff_df}\n")
        # Will add meets_all_affordable and share_affordable_at_crit2 after they're computed
        f.write("="*80 + "\n")

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
                recommendation = "recommended" if meets_all_affordable else "not_recommended"
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

    # DEBUG: Write decision variables to log
    debug_file = "adat_debug.log"
    with open(debug_file, "a") as f:
        f.write(f"[DEBUG] DECISION LOGIC RESULTS:\n")
        f.write(f"[DEBUG] share_affordable_at_crit2: {share_affordable_at_crit2}\n")
        if risk_level == "high":
            meets_all_affordable = (aff_df.loc[2, "aff_proj"] == proj_size)
            f.write(f"[DEBUG] meets_all_affordable: {meets_all_affordable}\n")
        if risk_level == "low" or risk_level == "unknown":
            share_50_or_below = (aff_df.loc[1, "aff_proj"] / proj_size) if proj_size else 0
            f.write(f"[DEBUG] share_50_or_below: {share_50_or_below}\n")
        f.write(f"[DEBUG] recommendation: {recommendation}\n")
        f.write("="*80 + "\n\n")

    # Return structured result
    return {
        "success": True,
        "recommendation": recommendation,
        "messages": messages,
        "risk_level": risk_level,
        "bgid": bgid,
        "bgid_resolution": resolution_details,
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