# ---------------------------------------------------------------
# CHUNK 1 — IMPORTS AND HELPER FUNCTIONS
# ---------------------------------------------------------------

import os
import re
import zipfile
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.ops import unary_union
from shapely.geometry import Point
from pathlib import Path

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Base directories
BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
PRE = DATA / "prepackaged"
NHGIS = DATA / "nhgis"
OUTPUT = BASE / "DHNA" / "data"
OUTPUT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------
# HELPER: median linear interpolation (R's med_lin_est)
# ---------------------------------------------------------------
def med_lin_est(names, values):
    """
    Python translation of R's median-linear interpolation function.
    names: list-like of variable names e.g. ['rent_100','rent_149',...]
    values: list-like counts corresponding to bins

    Returns median estimate.
    """
    vals = np.array(values, dtype=float)
    if vals.sum() == 0:
        return np.nan

    # locate bin where cumulative crosses 50%
    cum = vals.cumsum() / vals.sum()
    try:
        mp = np.where(cum > 0.5)[0][0]
    except IndexError:
        return np.nan

    # extract bin numeric values
    def bin_number(name):
        m = re.search(r"_(\d+)", name)
        return float(m.group(1)) if m else np.nan

    bin_1 = bin_number(names[mp])
    if mp > 0:
        bin_0 = bin_number(names[mp - 1])
        inc_width = bin_1 - bin_0
        inc_ratio = (vals.sum()/2 - vals[:mp].sum()) / vals[mp]
        return bin_0 + inc_ratio * inc_width

    # If mp == 0 (first bin holds median)
    # replicate R fallback
    next_bin = bin_number(names[mp + 1])
    inc_ratio_1 = 0.5 / (vals[0] / vals.sum())
    return next_bin * inc_ratio_1


# ---------------------------------------------------------------
# HELPER: renter FMI cutoff adjustment (R's renter_adj)
# ---------------------------------------------------------------
def renter_adj(names, values, fmi):
    inc_bins = np.array([float(re.search(r"_(\d+)", name).group(1)) for name in names])
    vals = np.array(values, dtype=float)
    mp_candidates = np.where(inc_bins > fmi)[0]
    if len(mp_candidates) == 0:
        return vals.sum()

    mp = mp_candidates[0]
    bin1 = inc_bins[mp]
    bin0 = inc_bins[mp - 1]
    inc_width = bin1 - bin0
    bin_ratio = (inc_width - (bin1 - fmi)) / inc_width
    adjusted = round(vals[:mp].sum() + vals[mp] * bin_ratio)
    return adjusted


# ---------------------------------------------------------------
# HELPER: Load NHGIS CSV (R's read_nhgis)
# ---------------------------------------------------------------
# ---------------------------------------------------------------
# HELPER: Load NHGIS CSV (R's read_nhgis) - FIXED VERSION
# ---------------------------------------------------------------
def read_nhgis(path):
    """
    Reads all NHGIS CSVs from a directory OR a single CSV file.
    Automatically extracts ZIP files if needed.
    """
    path = Path(path)

    # If the path is a directory → load all CSV files inside it
    if path.is_dir():
        # First, check for and extract any ZIP files
        zip_files = list(path.glob("*_csv.zip"))
        if zip_files:
            print(f"  - Found {len(zip_files)} ZIP file(s) in {path.name}, extracting...")
        for zip_file in zip_files:
            print(f"    • Extracting {zip_file.name}...")
            try:
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    zip_ref.extractall(path)
                print(f"      ✓ Extracted")
            except Exception as e:
                print(f"      ✗ Error: {e}")
        
        # Now find CSV files (including in subdirectories created by extraction)
        csv_files = sorted(path.rglob("*.csv"))
        if len(csv_files) == 0:
            raise FileNotFoundError(f"No CSVs found in {path} even after extraction")
        
        print(f"  - Found {len(csv_files)} CSV file(s), loading...")
        dfs = []
        for csv in csv_files:
            try:
                df = pd.read_csv(csv, low_memory=False, encoding='latin-1')
                dfs.append(df)
                print(f"    ✓ Loaded {csv.name} ({len(df)} rows)")
            except Exception as e:
                print(f"    ✗ Error loading {csv.name}: {e}")
        
        if not dfs:
            raise ValueError(f"Could not load any CSV files from {path}")
        
        return pd.concat(dfs, ignore_index=True)

    # If the path is a single CSV file
    elif path.suffix.lower() == ".csv":
        return pd.read_csv(path, low_memory=False, encoding='latin-1')

    else:
        raise ValueError(f"Invalid NHGIS path: {path}")
# HELPER: safe merge that behaves like R's left_join
# ---------------------------------------------------------------
def left_join(x, y, left_on=None, right_on=None, **kwargs):
    return x.merge(y, how="left", left_on=left_on, right_on=right_on, **kwargs)


print("CHUNK 1 loaded successfully.")

# ---------------------------------------------------------------
# CHUNK 2 — NHGIS 1990 → 2020 ETHNORACIAL STANDARDIZATION
# ---------------------------------------------------------------

print("CHUNK 2: Loading NHGIS 1990 block data...")

# Locate 1990 block file
nhgis_1990_dir = NHGIS / "block" / "bl1990"
nhgis_1990_files = list(nhgis_1990_dir.rglob("*.csv"))
if len(nhgis_1990_files) == 0:
    raise FileNotFoundError("No 1990 NHGIS block files found.")

bl1990 = read_nhgis(nhgis_1990_files[0])

# Reproduce R's mutate()
bl1990["pop"] = bl1990.loc[:, "ET2001":"ET2010"].sum(axis=1)
bl1990["pop_latino"] = bl1990.loc[:, "ET2006":"ET2010"].sum(axis=1)

bl1990 = bl1990.rename(columns={
    "ET2001": "pop_white",
    "ET2002": "pop_black",
    "ET2003": "pop_indigenous",
    "ET2004": "pop_asian",
    "ET2005": "pop_other"
})[
    [
        "GISJOIN", "pop", "pop_white", "pop_black", "pop_indigenous",
        "pop_asian", "pop_other", "pop_latino"
    ]
]


# -------------------------
# Crosswalk 1990 → 2010
# -------------------------
print("CHUNK 2: Crosswalking 1990 → 2010...")

xwalk90_10 = list((NHGIS / "crosswalks").glob("nhgis_blk1990_bg2010*.csv"))
if len(xwalk90_10) == 0:
    raise FileNotFoundError("Missing nhgis_blk1990_bg2010 crosswalk.")

cw90_10 = read_nhgis(xwalk90_10[0])

# Join by blk1990gj = GISJOIN
bl90xbg10 = cw90_10.merge(
    bl1990,
    how="left",
    left_on="blk1990gj",
    right_on="GISJOIN"
)

# Apply weights
pop_cols = ["pop", "pop_white", "pop_black", "pop_indigenous",
            "pop_asian", "pop_other", "pop_latino"]

for col in pop_cols:
    bl90xbg10[col] = bl90xbg10[col] * bl90xbg10["weight"]

# Collapse to BG2010
bl90xbg10 = (
    bl90xbg10
    .groupby(["bg2010gj", "bg2010ge"], as_index=False)[pop_cols]
    .sum()
)


# -------------------------
# Crosswalk 2010 → 2020
# -------------------------
print("CHUNK 2: Crosswalking 2010 → 2020...")

xwalk10_20 = list((NHGIS / "crosswalks").glob("nhgis_bg2010_bg2020*.csv"))
if len(xwalk10_20) == 0:
    raise FileNotFoundError("Missing nhgis_bg2010_bg2020 crosswalk.")

cw10_20 = read_nhgis(xwalk10_20[0])

# Join 1990→2010 data to 2010→2020 crosswalk
bg90_20 = cw10_20.merge(
    bl90xbg10,
    how="left",
    left_on="bg2010gj",
    right_on="bg2010gj"
)

# Apply population weights
for col in pop_cols:
    bg90_20[col] = bg90_20[col] * bg90_20["wt_pop"]

# Summarize to BG2020
bg90_20 = (
    bg90_20
    .groupby(["bg2020gj", "bg2020ge"], as_index=False)[pop_cols]
    .sum()
)

bg90_20["data_yr"] = 1990
bg90_20 = bg90_20.rename(columns={
    "bg2020gj": "GISJOIN",
    "bg2020ge": "GEOID"
})
bg90_20["GEOID"] = bg90_20["GEOID"].astype(str)

print("CHUNK 2 completed successfully.")

# ---------------------------------------------------------------
# CHUNK 3 — NHGIS 2000 → 2020 ETHNORACIAL STANDARDIZATION
# ---------------------------------------------------------------

print("\nCHUNK 3: Loading NHGIS 2000 block data...")

nhgis_2000_files = list((NHGIS / "block" / "bl2000").rglob("*.csv"))
if len(nhgis_2000_files) == 0:
    raise FileNotFoundError("No 2000 NHGIS block CSV files found.")

print(f"Found {len(nhgis_2000_files)} files. Using: {nhgis_2000_files[0].name}")

bl2000 = read_nhgis(nhgis_2000_files[0])

# Reproduce R calculations
# pop = FYF001:FYF014
fyf_cols = [col for col in bl2000.columns if col.startswith("FYF")]

bl2000["pop"] = bl2000.loc[:, "FYF001":"FYF014"].sum(axis=1)
bl2000["pop_latino"] = bl2000.loc[:, "FYF008":"FYF014"].sum(axis=1)
bl2000["pop_asian"] = bl2000["FYF004"] + bl2000["FYF005"]
bl2000["pop_other"] = bl2000["FYF006"] + bl2000["FYF007"]

bl2000 = bl2000.rename(columns={
    "FYF001": "pop_white",
    "FYF002": "pop_black",
    "FYF003": "pop_indigenous"
})

# Keep only R-selected columns
bl2000 = bl2000[[
    "GISJOIN", "pop", "pop_white", "pop_black", "pop_indigenous",
    "pop_asian", "pop_other", "pop_latino"
]]

bl2000["data_yr"] = 2000

print("CHUNK 3 completed successfully.")


# ---------------------------------------------------------------
# CHUNK 4 — NHGIS 2010 SOCIOECONOMIC STANDARDIZATION TO 2020 BG
# ---------------------------------------------------------------

print("CHUNK 4: Loading NHGIS 2010 block group socioeconomic data...")

nhgis_2010_bg_dir = NHGIS / "blockgroup" / "bg2010"
nhgis_2010_files = list(nhgis_2010_bg_dir.rglob("*.csv"))

if len(nhgis_2010_files) == 0:
    raise FileNotFoundError("No 2010 NHGIS block group files found.")

bg2010 = read_nhgis(nhgis_2010_files[0])

# ---------------------------------------------------------------
# Reproduce ALL renames and derived variables from R exactly
# ---------------------------------------------------------------

# Asian + Other categories
bg2010["pop_asian"] = bg2010["UEYE006"] + bg2010["UEYE007"]
bg2010["pop_other"] = bg2010["UEYE008"] + bg2010["UEYE009"]

# Adult education
bg2010["adult_less_than_HS"] = bg2010.loc[:, "UGSE002":"UGSE016"].sum(axis=1)
bg2010["adult_college_above"] = bg2010.loc[:, "UGSE022":"UGSE025"].sum(axis=1)

# Main renames
rename_2010 = {
    "UEYE001": "pop",
    "UGSE001": "adult_over25",
    "UEYE003": "pop_white",
    "UEYE004": "pop_black",
    "UEYE012": "pop_latino",
    "UEYE005": "pop_indigenous",
    "UKNE001": "HU",
    "UKNE002": "HH",
    "UKNE003": "HU_vacant",
    "UL8E001": "rent_HU",
    "GEO_ID": "GEOID"
}

# Rent bins
rent_bins_2010 = {
    "UL8E024": "rent_0",
    "UL8E003": "rent_100",
    "UL8E004": "rent_149",
    "UL8E005": "rent_199",
    "UL8E006": "rent_249",
    "UL8E007": "rent_299",
    "UL8E008": "rent_349",
    "UL8E009": "rent_399",
    "UL8E010": "rent_449",
    "UL8E011": "rent_499",
    "UL8E012": "rent_549",
    "UL8E013": "rent_599",
    "UL8E014": "rent_649",
    "UL8E015": "rent_699",
    "UL8E016": "rent_749",
    "UL8E017": "rent_799",
    "UL8E018": "rent_899",
    "UL8E019": "rent_999",
    "UL8E020": "rent_1249",
    "UL8E021": "rent_1499",
    "UL8E022": "rent_1999",
    "UL8E023": "rent_2000"
}

rename_2010.update(rent_bins_2010)

# Home value bins
hv_bins_2010 = {
    "UMKE002": "HV_10000",
    "UMKE003": "HV_14999",
    "UMKE004": "HV_19999",
    "UMKE005": "HV_24999",
    "UMKE006": "HV_29999",
    "UMKE007": "HV_34999",
    "UMKE008": "HV_39999",
    "UMKE009": "HV_49999",
    "UMKE010": "HV_59999",
    "UMKE011": "HV_69999",
    "UMKE012": "HV_79999",
    "UMKE013": "HV_89999",
    "UMKE014": "HV_99999",
    "UMKE015": "HV_124999",
    "UMKE016": "HV_149999",
    "UMKE017": "HV_174999",
    "UMKE018": "HV_199999",
    "UMKE019": "HV_249999",
    "UMKE020": "HV_299999",
    "UMKE021": "HV_399999",
    "UMKE022": "HV_499999",
    "UMKE023": "HV_749999",
    "UMKE024": "HV_999999",
    "UMKE025": "HV_1000000",
}

rename_2010.update(hv_bins_2010)

# Household income bins
hhinc_bins_2010 = {
    "UHCE002": "HHINC_10000",
    "UHCE003": "HHINC_14999",
    "UHCE004": "HHINC_19999",
    "UHCE005": "HHINC_24999",
    "UHCE006": "HHINC_29999",
    "UHCE007": "HHINC_34999",
    "UHCE008": "HHINC_39999",
    "UHCE009": "HHINC_44999",
    "UHCE010": "HHINC_49999",
    "UHCE011": "HHINC_59999",
    "UHCE012": "HHINC_74999",
    "UHCE013": "HHINC_99999",
    "UHCE014": "HHINC_124999",
    "UHCE015": "HHINC_149999",
    "UHCE016": "HHINC_199999",
    "UHCE017": "HHINC_250000",
}

rename_2010.update(hhinc_bins_2010)

bg2010 = bg2010.rename(columns=rename_2010)

# Remove unused variables (matches R's select(-starts_with("U")))
bg2010 = bg2010[[c for c in bg2010.columns if not c.startswith("U")]]

# Remove metadata columns
drop_cols = ["YEAR", "NAME_E", "NAME_M"]
for c in drop_cols:
    if c in bg2010.columns:
        bg2010 = bg2010.drop(columns=[c])

# ---------------------------------------------------------------
# CROSSWALK 2010 → 2020 (SOCIOECONOMIC)
# ---------------------------------------------------------------

print("CHUNK 4: Crosswalking 2010 → 2020 socioeconomic variables...")

# Join with 2010→2020 crosswalk
bg10_20 = cw10_20.merge(
    bg2010,
    how="left",
    left_on="bg2010gj",
    right_on="GISJOIN"
)

# Apply all weight types EXACTLY like R
for col in bg2010.columns:
    if col.startswith("pop"):
        bg10_20[col] = bg10_20[col] * bg10_20["wt_pop"]
    if col.startswith("adult"):
        bg10_20[col] = bg10_20[col] * bg10_20["wt_adult"]
    if col.startswith("HU") or col.startswith("HH"):
        bg10_20[col] = bg10_20[col] * bg10_20["wt_hu"]
    if col.startswith("rent"):
        bg10_20[col] = bg10_20[col] * bg10_20["wt_renthu"]
    if col.startswith("HV"):
        bg10_20[col] = bg10_20[col] * bg10_20["wt_ownhu"]

# Collapse to BG2020
group_cols = [c for c in bg2010.columns if c not in ["GISJOIN"]]

bg10_20 = (
    bg10_20
    .groupby(["bg2020gj", "bg2020ge"], as_index=False)[group_cols]
    .sum(min_count=1)
)

bg10_20["data_yr"] = 2010

bg10_20 = bg10_20.rename(columns={
    "bg2020gj": "GISJOIN",
    "bg2020ge": "GEOID"
})

bg10_20["GEOID"] = bg10_20["GEOID"].astype(str)

print("CHUNK 4 complete.")

# ---------------------------------------------------------------
# CHUNK 5 — Load + Format NHGIS 2020 Socioeconomic Data
# ---------------------------------------------------------------

print("CHUNK 5: Loading 2020 NHGIS block group socioeconomic data...")

nhgis_2020_bg_dir = NHGIS / "blockgroup" / "bg2020"
nhgis_2020_dirs = [d for d in nhgis_2020_bg_dir.iterdir() if d.is_dir()]

if len(nhgis_2020_dirs) == 0:
    raise FileNotFoundError("No NHGIS block group folders found in bg2020.")

bg2020 = read_nhgis(nhgis_2020_dirs[0])

# ---------------------------------------------------------------
# Derived variables (exact match to R)
# ---------------------------------------------------------------

bg2020["pop_asian"] = bg2020["ASOAE006"] + bg2020["ASOAE007"]
bg2020["pop_other"] = bg2020["ASOAE008"] + bg2020["ASOAE009"]

bg2020["adult_less_than_HS"] = bg2020.loc[:, "ASP3E002":"ASP3E016"].sum(axis=1)
bg2020["adult_college_above"] = bg2020.loc[:, "ASP3E022":"ASP3E025"].sum(axis=1)

# Extract GEOID from "GEO_ID"
bg2020["GEOID"] = bg2020["GEO_ID"].str.extract(r"(?<=S)(.*)")

# ---------------------------------------------------------------
# Rename columns (ALL from R)
# ---------------------------------------------------------------

rename_2020 = {
    "ASOAE001": "pop",
    "ASP3E001": "adult_over25",
    "ASOAE003": "pop_white",
    "ASOAE004": "pop_black",
    "ASOAE012": "pop_latino",
    "ASOAE005": "pop_indigenous",
    "ASS8E001": "HU",
    "ASS8E003": "HU_vacant",
    "ASS8E002": "HH",
    "ASVAE001": "rent_HU",
    "GEO_ID": "GEOID"
}

# Rent bins (FULL match)
rent_bins_2020 = {
    "ASVAE027": "rent_0",
    "ASVAE003": "rent_100",
    "ASVAE004": "rent_149",
    "ASVAE005": "rent_199",
    "ASVAE006": "rent_249",
    "ASVAE007": "rent_299",
    "ASVAE008": "rent_349",
    "ASVAE009": "rent_399",
    "ASVAE010": "rent_449",
    "ASVAE011": "rent_499",
    "ASVAE012": "rent_549",
    "ASVAE013": "rent_599",
    "ASVAE014": "rent_649",
    "ASVAE015": "rent_699",
    "ASVAE016": "rent_749",
    "ASVAE017": "rent_799",
    "ASVAE018": "rent_899",
    "ASVAE019": "rent_999",
    "ASVAE020": "rent_1249",
    "ASVAE021": "rent_1499",
    "ASVAE022": "rent_1999",
    "ASVAE023": "rent_2499",
    "ASVAE024": "rent_2999",
    "ASVAE025": "rent_3499",
    "ASVAE026": "rent_3500"
}

rename_2020.update(rent_bins_2020)

# Home value bins
hv_bins_2020 = {
    "ASVLE002": "HV_10000",
    "ASVLE003": "HV_14999",
    "ASVLE004": "HV_19999",
    "ASVLE005": "HV_24999",
    "ASVLE006": "HV_29999",
    "ASVLE007": "HV_34999",
    "ASVLE008": "HV_39999",
    "ASVLE009": "HV_49999",
    "ASVLE010": "HV_59999",
    "ASVLE011": "HV_69999",
    "ASVLE012": "HV_79999",
    "ASVLE013": "HV_89999",
    "ASVLE014": "HV_99999",
    "ASVLE015": "HV_124999",
    "ASVLE016": "HV_149999",
    "ASVLE017": "HV_174999",
    "ASVLE018": "HV_199999",
    "ASVLE019": "HV_249999",
    "ASVLE020": "HV_299999",
    "ASVLE021": "HV_399999",
    "ASVLE022": "HV_499999",
    "ASVLE023": "HV_749999",
    "ASVLE024": "HV_999999",
    "ASVLE025": "HV_1499999",
    "ASVLE026": "HV_1999999",
    "ASVLE027": "HV_2000000",
}

rename_2020.update(hv_bins_2020)

# HH income bins
hhinc_bins_2020 = {
    "ASQOE002": "HHINC_10000",
    "ASQOE003": "HHINC_14999",
    "ASQOE004": "HHINC_19999",
    "ASQOE005": "HHINC_24999",
    "ASQOE006": "HHINC_29999",
    "ASQOE007": "HHINC_34999",
    "ASQOE008": "HHINC_39999",
    "ASQOE009": "HHINC_44999",
    "ASQOE010": "HHINC_49999",
    "ASQOE011": "HHINC_59999",
    "ASQOE012": "HHINC_74999",
    "ASQOE013": "HHINC_99999",
    "ASQOE014": "HHINC_124999",
    "ASQOE015": "HHINC_149999",
    "ASQOE016": "HHINC_199999",
    "ASQOE017": "HHINC_250000"
}

rename_2020.update(hhinc_bins_2020)

# Apply renames
bg2020 = bg2020.rename(columns=rename_2020)

# ---------------------------------------------------------------
# Remove columns starting with "AS" AND metadata columns
# ---------------------------------------------------------------
bg2020 = bg2020[[c for c in bg2020.columns if not c.startswith("AS")]]

for col in ["YEAR", "NAME_E", "NAME_M"]:
    if col in bg2020.columns:
        bg2020 = bg2020.drop(columns=[col])

# ---------------------------------------------------------------
# Final filtering + flagging
# ---------------------------------------------------------------

bg2020 = bg2020[bg2020["pop"] > 0].copy()
bg2020["data_yr"] = 2020
bg2020["GEOID"] = bg2020["GEOID"].astype(str)

print("CHUNK 5 complete.")

# ---------------------------------------------------------------
# CHUNK 6 — Consolidate 2010 + 2020 socioeconomic data
# ---------------------------------------------------------------

print("CHUNK 6: Consolidating socioeconomic data (2010 + 2020)...")

# Remove duplicated columns to allow concat
bg10_20 = bg10_20.loc[:, ~bg10_20.columns.duplicated()]
bg2020  = bg2020.loc[:, ~bg2020.columns.duplicated()]

# Combine socioeconomic data
bg_data10_20 = pd.concat([bg10_20, bg2020], ignore_index=True)

print(f"CHUNK 6 complete. Combined rows: {len(bg_data10_20)}")


# ---------------------------------------------------------------
# CHUNK 7 — Local Area Unit Construction
# ---------------------------------------------------------------

print("CHUNK 7: Creating Local Area Units...")

import geopandas as gpd
from shapely.geometry import Point

# ----------------------------
# BG POPULATION (2020)
# ----------------------------

bg_pop20 = bg2020[['GISJOIN', 'pop']].copy()

# ----------------------------
# TRACT POPULATION (aggregate BG → CT)
# ----------------------------

ct_pop20 = (
    bg2020[['GISJOIN', 'pop']]
    .assign(GISJOIN_CT=lambda df: df['GISJOIN'].str.slice(stop=-1))
    .groupby('GISJOIN_CT', as_index=False)
    .agg(pop_ct=('pop', 'sum'))
)

# ----------------------------
# LOAD BLOCK GROUP SHAPEFILES
# ----------------------------

# 2023 Block Group polygons
lvm_bg_geo = gpd.read_file(
    "data/nhgis/gis/blockgroup/bg2023/KY_Jefferson_BG_2023.shp"
).to_crs(4326)

lvm_bg_geo = (
    lvm_bg_geo.merge(bg_pop20, on='GISJOIN', how='left')
              .query("pop > 0")
              .loc[:, ['GISJOIN', 'GEOID', 'geometry']]
              .rename(columns={'GISJOIN': 'GISJOIN_BG',
                               'GEOID': 'GEOID_BG'})
)

# 2020 Population Centers
lvm_bg_popctr_geo = gpd.read_file(
    "data/nhgis/gis/blockgroup/bgc2020/KY_Jefferson_BGC_2020.shp"
).to_crs(4326)

lvm_bg_popctr_geo = (
    lvm_bg_popctr_geo.merge(bg_pop20, on='GISJOIN', how='left')
                     .query("pop > 0")
                     .loc[:, ['GISJOIN', 'GEOID', 'pop', 'geometry']]
                     .rename(columns={'GISJOIN': 'GISJOIN_BG_PC',
                                      'GEOID': 'GEOID_BG_PC',
                                      'pop': 'pop_bg'})
)

# ----------------------------
# MATCH BG with CT membership
# ----------------------------
bg_ct_match = (
    bg_pop20
    .assign(GISJOIN_CT=lambda df: df['GISJOIN'].str.slice(stop=-1))
    .rename(columns={'GISJOIN': 'GISJOIN_comp'})
)

# ----------------------------
# SPATIAL JOIN — within 800m
# ----------------------------

print("   - Performing 800m population-center proximity join...")

local_area_raw = (
    gpd.sjoin_nearest(
        lvm_bg_geo,
        lvm_bg_popctr_geo,
        how="left",
        max_distance=800
    )
    .drop(columns=['index_right'])
)

# Convert to dataframe for processing
local_area_raw = pd.DataFrame(local_area_raw)
local_area_raw['GISJOIN_CT'] = local_area_raw['GISJOIN_BG_PC'].str.slice(stop=-1)

# ----------------------------
# ADD CT POPULATION TOTALS
# ----------------------------

local_area_raw = (
    local_area_raw
    .merge(ct_pop20, on='GISJOIN_CT', how='left')
    .groupby(['GISJOIN_BG', 'GISJOIN_CT'], as_index=False)
    .agg(
        pop_in_CT=('pop_bg', 'sum'),
        pop_ct=('pop_ct', 'mean')
    )
)

# ----------------------------
# FILTER BG WHERE >=50% OF CT POP LIVES WITHIN 800m
# ----------------------------

local_area_filtered = (
    local_area_raw
    .assign(pct_in_CT=lambda df: df['pop_in_CT'] / df['pop_ct'])
    .query("pct_in_CT >= 0.5")
)

# ----------------------------
# COMPLETE LOCAL AREA DEFINITION (Match BG-to-BG)
# ----------------------------

local_area = (
    local_area_filtered
    .merge(bg_ct_match, on='GISJOIN_CT', how='left')
    .rename(columns={
        'GISJOIN_BG': 'GISJOIN_proj',   # project BG (the LA unit)
        'GISJOIN_comp': 'GISJOIN_comp', # comparison BGs in same CT
        'pop': 'pop_BG'
    })
)

print("CHUNK 7 complete.")
print(f"   Local area rows: {len(local_area)}")
print("------------------------------------------------------------\n")

print("90 cols:", bg90_20.columns)
print("00 cols:", bl2000.columns)
print("10 cols:", bg10_20.columns)
print("20 cols:", bg2020.columns)

# ---------------------------------------------------------------
# CHUNK 8 — Population & Ethnoracial Change (1990–2020)
# ---------------------------------------------------------------

print("CHUNK 8: Processing ethnoracial population data...")

# --------------------------------------------------------------------
# 1. DEFINE ETHNORACIAL VARIABLES EXACTLY AS R USES (avoids bad merges)
# --------------------------------------------------------------------
ethno_cols = [
    "GISJOIN", "pop", "pop_white", "pop_black", "pop_indigenous",
    "pop_asian", "pop_other", "pop_latino", "data_yr"
]

# Guarantee columns exist in each frame
def subset_ethno(df):
    return df[[c for c in ethno_cols if c in df.columns]].copy()

# --------------------------------------------------------------------
# 2. COMBINE 1990 + 2000 + 2010 + 2020 POPULATION DATA
# --------------------------------------------------------------------
pop_ethnorace = pd.concat([
    subset_ethno(bg90_20),
    subset_ethno(bl2000),
    subset_ethno(bg10_20),
    subset_ethno(bg2020)
], ignore_index=True)

# Clean and round population fields
pop_cols = [c for c in ethno_cols if c.startswith("pop")]
for c in pop_cols:
    pop_ethnorace[c] = pop_ethnorace[c].round().astype(int)

print(f"   - pop_ethnorace combined: {pop_ethnorace.shape}")

# --------------------------------------------------------------------
# 3. LOCAL AREA POPULATION (pop_s)
#     Merge Local Areas (CHUNK 7) w/ all available ethnoracial data
# --------------------------------------------------------------------
pop_s = local_area.merge(
    pop_ethnorace,
    left_on="GISJOIN_comp",
    right_on="GISJOIN",
    how="left"
)

# Preserve GISJOIN_proj from local_area as the local‑area ID (project BG).
# GISJOIN_comp is used only for joining comparison BG attributes; do not overwrite GISJOIN_proj.

# Aggregate population to Local Area × Year
pop_s = (
    pop_s.groupby(["GISJOIN_proj", "data_yr"], as_index=False)
         .agg({col: "sum" for col in pop_cols})
)

pop_s["Area"] = "Local Area"
pop_s["group_id"] = pop_s["GISJOIN_proj"]

print(f"   - pop_s (local area): {pop_s.shape}")

# --------------------------------------------------------------------
# 4. MARKET AREAS (Jefferson County Market Areas)
# --------------------------------------------------------------------
print("   - Loading Market Area shapefile...")

# Must RETAIN geometry — critical for spatial join
Jefferson_ma = gpd.read_file(
    "data/prepackaged/Market_areas/Comp_Plan_Market_Areas.shp"
).to_crs(4326)

# Keep attributes R uses
Jefferson_ma = Jefferson_ma[["OBJECTID", "Name", "geometry"]]
Jefferson_ma = Jefferson_ma.rename(columns={"Name": "market_area"})

# Save to DHNA/data/gis/ (R also writes shapefile)
Jefferson_ma.to_file(
    "DHNA/data/gis/Comp_Plan_Market_Areas.shp",
    driver="ESRI Shapefile"
)

# --------------------------------------------------------------------
# 5. SPATIAL JOIN — Population Centers to Market Areas
# --------------------------------------------------------------------
print("   - Joining BG population centers to Market Areas...")

Jefferson_bg_ma = gpd.sjoin(
    lvm_bg_popctr_geo,     # BG population center points
    Jefferson_ma,          # Market area polygons
    how="left",
    predicate="intersects"
)

# Drop rows not assigned to a market area
Jefferson_bg_ma = Jefferson_bg_ma.dropna(subset=["market_area"])

# Join ethnoracial population to population-center BGs
Jefferson_bg_ma = Jefferson_bg_ma.merge(
    pop_ethnorace,
    left_on="GISJOIN_BG_PC",
    right_on="GISJOIN",
    how="left"
)

Jefferson_bg_ma["Area"] = "Market Area"

# Format column names to match R
Jefferson_bg_ma = (
    Jefferson_bg_ma
    .drop(columns=["GEOID", "pop_bg", "GEOID_BG_PC"], errors="ignore")
    .rename(columns={
        "GISJOIN_BG_PC": "GISJOIN",
        "market_area": "group_id"
    })
)

# Aggregate to Market Area × Year
Jefferson_bg_ma = (
    Jefferson_bg_ma.groupby(["group_id", "data_yr"], as_index=False)
                   .agg({col: "sum" for col in pop_cols})
)

print(f"   - Jefferson_bg_ma (market area): {Jefferson_bg_ma.shape}")

# --------------------------------------------------------------------
# 6. COMBINE LOCAL AREA + MARKET AREAS
# --------------------------------------------------------------------
pop_ma_s = pd.concat([pop_s, Jefferson_bg_ma], ignore_index=True)

# Output format: GISJOIN_proj = group_id
pop_ma_s = pop_ma_s.rename(columns={"GISJOIN": "GISJOIN_proj"})

print(f"   - Combined population dataset: {pop_ma_s.shape}")

# --------------------------------------------------------------------
# 7. WRITE OUTPUT
# --------------------------------------------------------------------
pop_ma_s.to_csv("DHNA/data/pop_ethnorace.csv", index=False)

print("CHUNK 8 complete.")
print("------------------------------------------------------------\n")

# ---------------------------------------------------------------
# CHUNK 9 — PUMS Housing Assessment Data
# ---------------------------------------------------------------

print("CHUNK 9: Processing PUMS housing assessment data...")

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

# ----------------------------
# HUD FMI income limits table
# ----------------------------

HUD_FMI = pd.DataFrame({
    "YEAR": [2023]*8 + [2022]*8 + [2021]*8,
    "NUMPREC": list(range(1, 9))*3,
    "MFI_ELI": [
        18850,21550,24240,26900,29100,31250,33400,35550,
        17800,20350,23030,27750,32470,37190,41910,46630,
        16150,18450,21960,26500,31040,35580,40120,44660
    ],
    "MFI_VLI": [
        31400,35900,40400,44850,48450,52050,55650,59250,
        29650,33900,38150,42350,45750,49150,52550,55950,
        26950,30800,34650,38450,41550,44650,47700,50800
    ],
    "MFI_LI": [
        50250,57400,64600,71750,77500,83250,89000,98750,
        47450,54200,61000,67750,73200,78600,84050,89450,
        43050,49200,55350,61500,66450,71350,76300,81200
    ]
})

# ----------------------------
# Load IPUMS ACS microdata
# ----------------------------

xml_file = "data/pums_usa/acs_21_23/usa_00001.xml"
dat_file = "data/pums_usa/acs_21_23/usa_00001.dat.gz"

try:
    # Read directly using pandas with column specifications from XML
    import xml.etree.ElementTree as ET
    
    print(f"   - Parsing {xml_file} for column specifications...")
    
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Find variable descriptions
    colspecs = []
    names = []
    
    for var in root.findall(".//{http://www.icpsr.umich.edu/DDI}var"):
        name = var.get('name')
        location = var.find('.//{http://www.icpsr.umich.edu/DDI}location')
        
        if location is not None:
            start = int(location.get('StartPos')) - 1  # 0-indexed
            width = int(location.get('width'))
            end = start + width
            
            colspecs.append((start, end))
            names.append(name)
    
    print(f"   - Found {len(names)} variables")
    print(f"   - Reading fixed-width file from {dat_file}...")
    
    # Read fixed-width format
    micro = pd.read_fwf(dat_file, colspecs=colspecs, names=names, 
                       compression='gzip', dtype=str)
    
    # Convert to numeric
    numeric_cols = ['YEAR', 'PUMA', 'HHINCOME', 'OWNERSHP', 'RENTGRS', 
                    'NUMPREC', 'SAMPLE', 'SERIAL', 'HHWT']
    for col in numeric_cols:
        if col in micro.columns:
            micro[col] = pd.to_numeric(micro[col], errors='coerce')
    
    print(f"   - Loaded IPUMS data: {micro.shape}")
    
except Exception as e:
    print(f"   - WARNING: Could not load IPUMS data: {type(e).__name__}: {e}")
    print("   - Skipping PUMS block.")
    micro = None

if micro is not None:
    
    print("   - Filtering to Jefferson County renters...")

    ky_h = micro[
        (micro["PUMA"].isin([1701, 1702, 1703, 1704, 1705, 1706])) &
        (micro["HHINCOME"] < 9999999) &
        (micro["OWNERSHP"] == 2)
    ].copy()

    print(f"   - Filtered to {len(ky_h)} renter households")

    if len(ky_h) == 0:
        print("   - WARNING: No households matched filter. Checking data...")
        print(f"     Available PUMAs: {sorted(micro['PUMA'].unique())[:10]}")
        print(f"     OWNERSHP values: {micro['OWNERSHP'].value_counts().to_dict()}")
    else:
        # Replace negatives with zero
        ky_h["HHINCOME"] = ky_h["HHINCOME"].clip(lower=0)

        # Create household ID
        ky_h["HH_ID"] = ky_h["SAMPLE"].astype(str) + "_" + ky_h["SERIAL"].astype(str)

        # Merge FMI limits
        ky_h = ky_h.merge(HUD_FMI, on=["YEAR", "NUMPREC"], how="left")

        # Income Brackets
        def income_level(row):
            inc = row["HHINCOME"]
            if inc < row["MFI_ELI"]:
                return "Below 30%  ($27,125)"
            elif row["MFI_ELI"] <= inc < row["MFI_VLI"]:
                return "30% to 50% ($40,400)"
            elif row["MFI_VLI"] <= inc < row["MFI_LI"]:
                return "50% to 80% ($64,625)"
            else:
                return "Above 80%"

        ky_h["HHINC_levels"] = ky_h.apply(income_level, axis=1)

        # Rent Brackets
        def rent_level(row):
            rent = row["RENTGRS"]
            if rent < (row["MFI_ELI"] * .3) / 12:
                return "Below 30%  ($678)"
            elif (row["MFI_ELI"] * .3) / 12 <= rent < (row["MFI_VLI"] * .3) / 12:
                return "30% to 50% ($1010)"
            elif (row["MFI_VLI"] * .3) / 12 <= rent < (row["MFI_LI"] * .3) / 12:
                return "50% to 80% ($1615)"
            else:
                return "Above 80%  (market)"

        ky_h["RENT_levels"] = ky_h.apply(rent_level, axis=1)

        # Rent Burden Categories
        def burden(row):
            inc = row["HHINCOME"]
            rent = row["RENTGRS"]
            if (inc * .3) / 12 > rent:
                return "No burden"
            elif (inc * .5) / 12 <= rent:
                return "Severely burdened"
            else:
                return "Burdened"

        ky_h["rent_burden"] = ky_h.apply(burden, axis=1)

        # Select final fields
        ky_h_final = ky_h[[
            "HHWT", "HHINC_levels", "RENT_levels", "RENTGRS", "rent_burden"
        ]].copy()

        # Write to CSV
        ky_h_final.to_csv("DHNA/data/hh_micro.csv", index=False)
        print("   - hh_micro.csv successfully written.")

print("CHUNK 9 complete.\n------------------------------------------------------------\n")

# ---------------------------------------------------------------
# CHUNK 10A — BG DATA FORMATTING: Population + Race Change
# ---------------------------------------------------------------

print("CHUNK 10A: Computing population & ethnoracial change...")

# Fix column name mismatch
if 'GISJOIN' in pop_s.columns and 'GISJOIN_proj' not in pop_s.columns:
    print("   - Renaming GISJOIN to GISJOIN_proj")
    pop_s = pop_s.rename(columns={'GISJOIN': 'GISJOIN_proj'})

# Drop unnecessary columns
pop_s = pop_s.drop(columns=['Area', 'group_id'], errors='ignore')

print(f"   - pop_s prepared: {pop_s.shape}")

# ----------------------------
# Extract 2000 population
# ----------------------------
pop00 = pop_s[pop_s["data_yr"] == 2000].copy()
pop00 = pop00.drop(columns=["data_yr"], errors='ignore')
# Rename ONLY the pop columns, keeping GISJOIN_proj unchanged
pop_cols_to_rename = {col: f"{col}_00" for col in pop00.columns if col.startswith("pop")}
pop00 = pop00.rename(columns=pop_cols_to_rename)

# ----------------------------
# Extract 2010 population
# ----------------------------
pop10 = pop_s[pop_s["data_yr"] == 2010].copy()
pop10 = pop10.drop(columns=["data_yr"], errors='ignore')
pop_cols_to_rename = {col: f"{col}_10" for col in pop10.columns if col.startswith("pop")}
pop10 = pop10.rename(columns=pop_cols_to_rename)

# ----------------------------
# Extract 2020 population
# ----------------------------
pop20 = pop_s[pop_s["data_yr"] == 2020].copy()
pop20 = pop20.drop(columns=["data_yr"], errors='ignore')
pop_cols_to_rename = {col: f"{col}_20" for col in pop20.columns if col.startswith("pop")}
pop20 = pop20.rename(columns=pop_cols_to_rename)

print(f"   - Extracted: pop00={len(pop00)}, pop10={len(pop10)}, pop20={len(pop20)}")

# ----------------------------
# JOIN population across 00 → 10 → 20
# ----------------------------
pop_change = pop00.merge(pop10, on="GISJOIN_proj", how="outer")
pop_change = pop_change.merge(pop20, on="GISJOIN_proj", how="outer")

print(f"   - Merged population: {pop_change.shape}")

# Equivalent of R: filter(pop_20 > 0)
pop_change = pop_change[pop_change["pop_20"] > 0].copy()

print(f"   - After filtering pop_20 > 0: {pop_change.shape}")

# ----------------------------
# Compute population changes (as R does)
# ----------------------------
pop_change["pop_change00_10"] = pop_change["pop_10"] - pop_change["pop_00"]
pop_change["pop_change10_20"] = pop_change["pop_20"] - pop_change["pop_10"]

# Race changes
pop_change["white_change00_10"] = pop_change["pop_white_10"] - pop_change["pop_white_00"]
pop_change["white_change10_20"] = pop_change["pop_white_20"] - pop_change["pop_white_10"]

pop_change["black_change00_10"] = pop_change["pop_black_10"] - pop_change["pop_black_00"]
pop_change["black_change10_20"] = pop_change["pop_black_20"] - pop_change["pop_black_10"]

pop_change["latino_change00_10"] = pop_change["pop_latino_10"] - pop_change["pop_latino_00"]
pop_change["latino_change10_20"] = pop_change["pop_latino_20"] - pop_change["pop_latino_10"]

# % Black share change 2000 → 2020
pop_change["blackpct_ch_00_20"] = (
    (pop_change["pop_black_20"] / pop_change["pop_20"]) -
    (pop_change["pop_black_00"] / pop_change["pop_00"])
)

print(f"   - Population change dataset: {pop_change.shape}")
print("CHUNK 10A complete.\n------------------------------------------------------------\n")
# ---------------------------------------------------------------
# CHUNK 10B — Median Rent (2010 & 2020)
# ---------------------------------------------------------------

print("CHUNK 10B: Calculating median rent for 2010 & 2020...")

import re

# ----------------------------
# Helper to extract numeric value from rent variable name
# e.g., "rent_749" -> 749
# ----------------------------
def extract_rent_value(name):
    match = re.search(r"_(\d+)$", name)
    return int(match.group(1)) if match else None


# -----------------------------------------------------------
# 2010 MEDIAN RENT
# -----------------------------------------------------------

# Select rent columns
rent_cols_2010 = [c for c in bg10_20.columns if c.startswith("rent_")]

med_rent10_raw = (
    local_area.merge(bg10_20, left_on="GISJOIN_comp", right_on="GISJOIN", how="left")
    .loc[:, ["GISJOIN_comp", "GISJOIN_proj"] + rent_cols_2010]
)

# Convert to long format
med_rent10_long = med_rent10_raw.melt(
    id_vars=["GISJOIN_comp", "GISJOIN_proj"],
    value_vars=rent_cols_2010,
    var_name="name",
    value_name="value"
)

# Group + sum values for each rent bin
med_rent10_grouped = (
    med_rent10_long.groupby(["GISJOIN_proj", "name"], as_index=False)
                   .agg({"value": "sum"})
)

# Add rent numeric bin
med_rent10_grouped["rent_val"] = med_rent10_grouped["name"].apply(extract_rent_value)

# Sort within each group
med_rent10_grouped = med_rent10_grouped.sort_values(["GISJOIN_proj", "rent_val"])

# Check sum filter (>= 100)
med_rent10_grouped["check_sum"] = (
    med_rent10_grouped.groupby("GISJOIN_proj")["value"].transform("sum")
)

med_rent10_filtered = med_rent10_grouped[med_rent10_grouped["check_sum"] > 100].copy()

# Compute median using R's med_lin_est logic
median_rent10 = (
    med_rent10_filtered.groupby("GISJOIN_proj")
    .apply(lambda df: med_lin_est(df["name"].tolist(), df["value"].tolist()))
    .reset_index()
)

median_rent10.columns = ["GISJOIN_proj", "median_rent_10"]

print("   - Finished median_rent_10:", median_rent10.shape)


# -----------------------------------------------------------
# 2020 MEDIAN RENT
# -----------------------------------------------------------

rent_cols_2020 = [c for c in bg2020.columns if c.startswith("rent_")]

med_rent20_raw = (
    local_area.merge(bg2020, left_on="GISJOIN_comp", right_on="GISJOIN", how="left")
    .loc[:, ["GISJOIN_comp", "GISJOIN_proj"] + rent_cols_2020]
)

med_rent20_long = med_rent20_raw.melt(
    id_vars=["GISJOIN_comp", "GISJOIN_proj"],
    value_vars=rent_cols_2020,
    var_name="name",
    value_name="value"
)

med_rent20_grouped = (
    med_rent20_long.groupby(["GISJOIN_proj", "name"], as_index=False)
                   .agg({"value": "sum"})
)

med_rent20_grouped["rent_val"] = med_rent20_grouped["name"].apply(extract_rent_value)

med_rent20_grouped = med_rent20_grouped.sort_values(["GISJOIN_proj", "rent_val"])

med_rent20_grouped["check_sum"] = (
    med_rent20_grouped.groupby("GISJOIN_proj")["value"].transform("sum")
)

med_rent20_filtered = med_rent20_grouped[med_rent20_grouped["check_sum"] > 100].copy()

median_rent20 = (
    med_rent20_filtered.groupby("GISJOIN_proj")
    .apply(lambda df: med_lin_est(df["name"].tolist(), df["value"].tolist()))
    .reset_index()
)

median_rent20.columns = ["GISJOIN_proj", "median_rent_20"]

print("   - Finished median_rent_20:", median_rent20.shape)

print("CHUNK 10B complete.\n------------------------------------------------------------\n")

# ---------------------------------------------------------------
# CHUNK 10C — Median Household Income (2010 & 2020)
# ---------------------------------------------------------------

print("CHUNK 10C: Calculating median household income for 2010 & 2020...")

# Helper to extract numeric income bin, same as rent
def extract_income_value(name):
    match = re.search(r"_(\d+)$", name)
    return int(match.group(1)) if match else None


# -----------------------------------------------------------
# 2010 MEDIAN HOUSEHOLD INCOME
# -----------------------------------------------------------

# Income columns in 2010 standardized data
inc_cols_2010 = [c for c in bg10_20.columns if c.startswith("HHINC_")]

med_hhinc10_raw = (
    local_area.merge(bg10_20, left_on="GISJOIN_comp", right_on="GISJOIN", how="left")
    .loc[:, ["GISJOIN_comp", "GISJOIN_proj"] + inc_cols_2010]
)

# Long format
med_hhinc10_long = med_hhinc10_raw.melt(
    id_vars=["GISJOIN_comp", "GISJOIN_proj"],
    value_vars=inc_cols_2010,
    var_name="name",
    value_name="value"
)

# Group & sum
med_hhinc10_grouped = (
    med_hhinc10_long.groupby(["GISJOIN_proj", "name"], as_index=False)
                    .agg({"value": "sum"})
)

# Income numeric bin
med_hhinc10_grouped["bin_val"] = med_hhinc10_grouped["name"].apply(extract_income_value)

# Sort bins
med_hhinc10_grouped = med_hhinc10_grouped.sort_values(["GISJOIN_proj", "bin_val"])

# Compute median with med_lin_est
median_hhinc10 = (
    med_hhinc10_grouped.groupby("GISJOIN_proj")
    .apply(lambda df: med_lin_est(df["name"].tolist(), df["value"].tolist()))
    .reset_index()
)

median_hhinc10.columns = ["GISJOIN_proj", "median_hhinc_10"]

print("   - Finished median_hhinc_10:", median_hhinc10.shape)


# -----------------------------------------------------------
# 2020 MEDIAN HOUSEHOLD INCOME
# -----------------------------------------------------------

inc_cols_2020 = [c for c in bg2020.columns if c.startswith("HHINC_")]

med_hhinc20_raw = (
    local_area.merge(bg2020, left_on="GISJOIN_comp", right_on="GISJOIN", how="left")
    .loc[:, ["GISJOIN_comp", "GISJOIN_proj"] + inc_cols_2020]
)

med_hhinc20_long = med_hhinc20_raw.melt(
    id_vars=["GISJOIN_comp", "GISJOIN_proj"],
    value_vars=inc_cols_2020,
    var_name="name",
    value_name="value"
)

med_hhinc20_grouped = (
    med_hhinc20_long.groupby(["GISJOIN_proj", "name"], as_index=False)
                    .agg({"value": "sum"})
)

med_hhinc20_grouped["bin_val"] = med_hhinc20_grouped["name"].apply(extract_income_value)
med_hhinc20_grouped = med_hhinc20_grouped.sort_values(["GISJOIN_proj", "bin_val"])

median_hhinc20 = (
    med_hhinc20_grouped.groupby("GISJOIN_proj")
    .apply(lambda df: med_lin_est(df["name"].tolist(), df["value"].tolist()))
    .reset_index()
)

median_hhinc20.columns = ["GISJOIN_proj", "median_hhinc_20"]

print("   - Finished median_hhinc_20:", median_hhinc20.shape)

print("CHUNK 10C complete.\n------------------------------------------------------------\n")

# ---------------------------------------------------------------
# CHUNK 10D — Median Home Value (2010 & 2020)
# ---------------------------------------------------------------

print("CHUNK 10D: Calculating median home value for 2010 & 2020...")

# Helper to extract numeric home value from variable name
def extract_hv_value(name):
    match = re.search(r"_(\d+)$", name)
    return int(match.group(1)) if match else None


# -----------------------------------------------------------
# 2010 MEDIAN HOME VALUE
# -----------------------------------------------------------

hv_cols_2010 = [c for c in bg10_20.columns if c.startswith("HV_")]

med_hv10_raw = (
    local_area.merge(bg10_20, left_on="GISJOIN_comp", right_on="GISJOIN", how="left")
    .loc[:, ["GISJOIN_comp", "GISJOIN_proj"] + hv_cols_2010]
)

med_hv10_long = med_hv10_raw.melt(
    id_vars=["GISJOIN_comp", "GISJOIN_proj"],
    value_vars=hv_cols_2010,
    var_name="name",
    value_name="value"
)

med_hv10_grouped = (
    med_hv10_long.groupby(["GISJOIN_proj", "name"], as_index=False)
                 .agg({"value": "sum"})
)

med_hv10_grouped["bin_val"] = med_hv10_grouped["name"].apply(extract_hv_value)
med_hv10_grouped = med_hv10_grouped.sort_values(["GISJOIN_proj", "bin_val"])

median_hv10 = (
    med_hv10_grouped.groupby("GISJOIN_proj")
    .apply(lambda df: med_lin_est(df["name"].tolist(), df["value"].tolist()))
    .reset_index()
)

median_hv10.columns = ["GISJOIN_proj", "median_hv_10"]

print("   - Finished median_hv_10:", median_hv10.shape)


# -----------------------------------------------------------
# 2020 MEDIAN HOME VALUE
# -----------------------------------------------------------

hv_cols_2020 = [c for c in bg2020.columns if c.startswith("HV_")]

med_hv20_raw = (
    local_area.merge(bg2020, left_on="GISJOIN_comp", right_on="GISJOIN", how="left")
    .loc[:, ["GISJOIN_comp", "GISJOIN_proj"] + hv_cols_2020]
)

med_hv20_long = med_hv20_raw.melt(
    id_vars=["GISJOIN_comp", "GISJOIN_proj"],
    value_vars=hv_cols_2020,
    var_name="name",
    value_name="value"
)

med_hv20_grouped = (
    med_hv20_long.groupby(["GISJOIN_proj", "name"], as_index=False)
                 .agg({"value": "sum"})
)

med_hv20_grouped["bin_val"] = med_hv20_grouped["name"].apply(extract_hv_value)
med_hv20_grouped = med_hv20_grouped.sort_values(["GISJOIN_proj", "bin_val"])

median_hv20 = (
    med_hv20_grouped.groupby("GISJOIN_proj")
    .apply(lambda df: med_lin_est(df["name"].tolist(), df["value"].tolist()))
    .reset_index()
)

median_hv20.columns = ["GISJOIN_proj", "median_hv_20"]

print("   - Finished median_hv_20:", median_hv20.shape)

print("CHUNK 10D complete.\n------------------------------------------------------------\n")
# ---------------------------------------------------------------
# CHUNK 10E — Neighborhood Vars, RentHub, Permits, AH, Final BG Data
# ---------------------------------------------------------------

print("CHUNK 10E: Constructing neighborhood variables & final BG dataset...")

# ===============================================================
# 1. NEIGHBORHOOD VARIABLES (2010)
# ===============================================================

nhood_vars10 = (
    local_area.merge(bg10_20, left_on="GISJOIN_comp", right_on="GISJOIN")
)

nhood_vars10["hi_inc_hh"] = nhood_vars10.filter(regex=r"HHINC_99999|HHINC_124999|HHINC_149999|HHINC_199999|HHINC_250000").sum(axis=1)
nhood_vars10["lo_inc_hh"] = nhood_vars10.filter(regex=r"HHINC_10000|HHINC_14999|HHINC_19999|HHINC_24999|HHINC_29999").sum(axis=1)

nhood_vars10_s = (
    nhood_vars10.groupby("GISJOIN_proj", as_index=False)
    .agg({
        "adult_college_above": "sum",
        "adult_over25": "sum",
        "rent_HU": "sum",
        "HU": "sum",
        "HU_vacant": "sum",
        "HH": "sum",
        "hi_inc_hh": "sum",
        "lo_inc_hh": "sum"
    })
)

nhood_vars10_s = nhood_vars10_s.rename(columns={
    "adult_college_above": "adult_college_above_10",
    "adult_over25": "adult_over25_10",
    "rent_HU": "renters_10",
    "HU": "HU_10",
    "HU_vacant": "HU_vacant_10",
    "HH": "HH_10",
    "hi_inc_hh": "hi_inc_hh_10",
    "lo_inc_hh": "lo_inc_hh_10",
})


# ===============================================================
# 2. NEIGHBORHOOD VARIABLES (2020)
# ===============================================================

nhood_vars20 = (
    local_area.merge(bg2020, left_on="GISJOIN_comp", right_on="GISJOIN")
)

nhood_vars20["hi_inc_hh"] = nhood_vars20.filter(regex=r"HHINC_124999|HHINC_149999|HHINC_174999|HHINC_199999|HHINC_249999|HHINC_299999|HHINC_399999|HHINC_499999|HHINC_749999|HHINC_999999|HHINC_1499999|HHINC_1999999|HHINC_2000000").sum(axis=1)
nhood_vars20["lo_inc_hh"] = nhood_vars20.filter(regex=r"HHINC_10000|HHINC_14999|HHINC_19999|HHINC_24999|HHINC_29999|HHINC_34999").sum(axis=1)

nhood_vars20_s = (
    nhood_vars20.groupby("GISJOIN_proj", as_index=False)
    .agg({
        "adult_college_above": "sum",
        "adult_over25": "sum",
        "rent_HU": "sum",
        "HU": "sum",
        "HU_vacant": "sum",
        "HH": "sum",
        "hi_inc_hh": "sum",
        "lo_inc_hh": "sum"
    })
)

nhood_vars20_s = nhood_vars20_s.rename(columns={
    "adult_college_above": "adult_college_above_20",
    "adult_over25": "adult_over25_20",
    "rent_HU": "renters_20",
    "HU": "HU_20",
    "HU_vacant": "HU_vacant_20",
    "HH": "HH_20",
    "hi_inc_hh": "hi_inc_hh_20",
    "lo_inc_hh": "lo_inc_hh_20",
})


# ===============================================================
# 3. RENTHUB BUFFER (Q3 2017 vs Q3 2024)
# ===============================================================

print("   - Processing RentHub buffer...")

rent_buffer = pd.read_csv("data/prepackaged/renthub/rent_buffer.csv")

rent_buffer["year_qu_text"] = rent_buffer["R_quarter"] + "_" + rent_buffer["R_year"].astype(str)
rb1 = rent_buffer[(rent_buffer["year_qu_text"].isin(["Q3_2017", "Q3_2024"])) & (rent_buffer["N"] > 30)].copy()

rb1["bg_n"] = rb1.groupby("GISJOIN")["GISJOIN"].transform("count")
rb1 = rb1[rb1["bg_n"] == 2].drop(columns=["bg_n"])

rent_buffer_wide = rb1.pivot_table(
    index=["GISJOIN", "GEOID_bg"],
    columns="year_qu_text",
    values=["rent_bg", "rent_ma"]
).reset_index()

rent_buffer_wide.columns = ["GISJOIN_proj", "GEOID_bg",
                            "rent_bg_Q3_2017", "rent_bg_Q3_2024",
                            "rent_ma_Q3_2017", "rent_ma_Q3_2024"]


# ===============================================================
# 4. RENTHUB — QUARTERLY DATA (2019–2024)
# ===============================================================

rb2 = rent_buffer.copy()
rb2 = rb2[(rb2["R_year"] > 2017) & (rb2["N"] > 30)]

rb2["bg_n"] = rb2.groupby("GISJOIN")["GISJOIN"].transform("count")
rb2 = rb2[rb2["bg_n"] > 20].drop(columns=["bg_n"])

rent_quarterly = rb2.rename(columns={"GISJOIN": "GISJOIN_proj"})
rent_quarterly.to_csv("DHNA/data/Renthub_quarterly_rent.csv", index=False)


# ===============================================================
# 5. PERMITS WITHIN 800 METERS
# ===============================================================

print("   - Loading permits...")

# Reproject block-group population centers to 2246
centers_2246 = lvm_bg_popctr_geo.to_crs(2246)

# Create 800m (2640 ft) buffers
buffer_geom = centers_2246.geometry.buffer(2640)

lvm_bg_popctr_buffer = gpd.GeoDataFrame(
    centers_2246[["GISJOIN_BG_PC"]].rename(columns={"GISJOIN_BG_PC": "GISJOIN_proj"}),
    geometry=buffer_geom,
    crs=2246
)

# Load permit shapefile
build_permits = gpd.read_file("data/prepackaged/permits/res_permits2.shp").to_crs(2246)

# Spatial join → count permits within buffer
bg_permits = (
    gpd.sjoin(lvm_bg_popctr_buffer, build_permits, predicate="intersects")
    .groupby("GISJOIN_proj", as_index=False)
    .size()
    .rename(columns={"size": "permits_N"})
)


# ===============================================================
# 6. AFFORDABLE HOUSING WITHIN 800 METERS
# ===============================================================

print("   - Loading affordable units...")

affordable = gpd.read_file("data/prepackaged/affordable/affordable_housing.shp").to_crs(2246)
affordable = affordable[["NHPD_Prope", "Property_N", "Total_Unit", "EndDate_Ye", "geometry"]]

bg_affordable = (
    gpd.sjoin(lvm_bg_popctr_buffer, affordable, predicate="intersects")
    .query("EndDate_Ye > 2026")
    .groupby("GISJOIN_proj", as_index=False)
    .agg({"Total_Unit": "sum"})
    .rename(columns={"Total_Unit": "affordable_units"})
)


# ===============================================================
# 7. FINAL BG DATA ASSEMBLY
# ===============================================================

print("   - Assembling final bg_data...")

bg_data = (
    pop_change.merge(median_rent10, on="GISJOIN_proj", how="left")
              .merge(median_rent20, on="GISJOIN_proj", how="left")
              .merge(median_hv10,   on="GISJOIN_proj", how="left")
              .merge(median_hv20,   on="GISJOIN_proj", how="left")
              .merge(median_hhinc10, on="GISJOIN_proj", how="left")
              .merge(median_hhinc20, on="GISJOIN_proj", how="left")
              .merge(nhood_vars10_s, on="GISJOIN_proj", how="left")
              .merge(nhood_vars20_s, on="GISJOIN_proj", how="left")
              .merge(rent_buffer_wide, on="GISJOIN_proj", how="left")
              .merge(bg_permits, on="GISJOIN_proj", how="left")
              .merge(bg_affordable, on="GISJOIN_proj", how="left")
)

# ===============================================================
# 8. DERIVED VARIABLES (identical to R logic)
# ===============================================================

bg_data["vacancy_Ch"] = (bg_data["HU_vacant_20"]/bg_data["HU_20"]) - (bg_data["HU_vacant_10"]/bg_data["HU_10"])
bg_data["HH_ch"] = bg_data["HH_20"] - bg_data["HH_10"]
bg_data["HU_ch"] = bg_data["HU_20"] - bg_data["HU_10"]
bg_data["housing_tightness"] = (bg_data["HU_ch"] - bg_data["HH_ch"]) / bg_data["HU_20"]

bg_data["HH_p_ch"] = (bg_data["HH_20"] - bg_data["HH_10"]) / bg_data["HH_10"]
bg_data["HU_p_ch"] = (bg_data["HU_20"] - bg_data["HU_10"]) / bg_data["HU_10"]

bg_data["renter_p_10"] = bg_data["renters_10"] / bg_data["HH_10"]
bg_data["renter_p_20"] = bg_data["renters_20"] / bg_data["HH_20"]
bg_data["renter_p_ch"] = bg_data["renter_p_20"] - bg_data["renter_p_10"]

# These need adult_over25_10 and adult_over25_20 available
bg_data["college_edu"] = (bg_data["adult_college_above_20"] / bg_data["adult_over25_20"]) - (
    bg_data["adult_college_above_10"] / bg_data["adult_over25_10"]
)

bg_data["hi_inc_ch"] = (bg_data["hi_inc_hh_20"] / bg_data["HH_20"]) - (bg_data["hi_inc_hh_10"] / bg_data["HH_10"])
bg_data["hi_inc_ch_pop"] = bg_data["hi_inc_hh_20"] - bg_data["hi_inc_hh_10"]

bg_data["lo_inc_ch"] = (bg_data["lo_inc_hh_20"] / bg_data["HH_20"]) - (bg_data["lo_inc_hh_10"] / bg_data["HH_10"])
bg_data["lo_inc_ch_pop"] = bg_data["lo_inc_hh_20"] - bg_data["lo_inc_hh_10"]

bg_data["hhinc_ch"] = (bg_data["median_hhinc_20"] - bg_data["median_hhinc_10"]) / bg_data["median_hhinc_10"]

print("CHUNK 10E complete.\n------------------------------------------------------------\n")

# ---------------------------------------------------------------
# CHUNK 11A — TRACT-LEVEL ACS (2020 ONLY)
# ---------------------------------------------------------------

print("CHUNK 11A: Loading tract-level ACS (2020 only)...")

from pathlib import Path

tract_path = Path("data/nhgis/tract")

# ------------------------------------------------
# 1. FIND 2020 TRACT CSV
# ------------------------------------------------
ct2020_files = list((tract_path / "ct2020").rglob("*_tract.csv"))
if len(ct2020_files) == 0:
    raise FileNotFoundError("No 2020 tract CSV found in data/nhgis/tract/ct2020/")
    
print(f"   - 2020 tract file detected: {ct2020_files[0].name}")

ct20 = pd.read_csv(ct2020_files[0])

# ------------------------------------------------
# 2. BASIC STANDARDIZATION
# ------------------------------------------------
# Standardize GISJOIN field name
if "GISJOIN" in ct20.columns:
    ct20 = ct20.rename(columns={"GISJOIN": "GISJOIN_CT"})
elif "GISJOIN_CT" not in ct20.columns:
    raise KeyError("Cannot find GISJOIN or GISJOIN_CT in tract file")

# Remove duplicate GISJOIN rows
ct20 = ct20.drop_duplicates(subset=["GISJOIN_CT"])

# Convert all numeric-looking columns
for col in ct20.columns:
    if ct20[col].dtype == "object":
        ct20[col] = pd.to_numeric(ct20[col], errors="ignore")

# ------------------------------------------------
# 3. SAVE tract-only dataset
# (No derived variables here: ACS 2020 tract dataset does NOT contain HH/HU/renters/etc.)
# ------------------------------------------------
ct_data = ct20.copy()

print("   - ct_data shape:", ct_data.shape)
print("CHUNK 11A complete.\n------------------------------------------------------------\n")

# -----------------------------------------------
# BUILD tract_chas FROM ct20 (tract ACS 2020 data)
# -----------------------------------------------

tract_cols_needed = [
    "GISJOIN_ct", "GEOID", 
    "ASWFE010", "ASWFE011", "ASWFE012",   # renter burden
    "ASWFE002", "ASWFE006",               # owner totals A/B
    "ASWFE003", "ASWFE007",               # owner burden30 A/B
    "ASWFE004", "ASWFE008",               # owner burden50 A/B
    "ASNQE001",                           # age total
    "ASPIE001",                           # HH total
    "AS8RE001"                            # disability total
]

# Keep only columns that actually exist in the tract file
tract_cols_available = [c for c in tract_cols_needed if c in ct20.columns]

tract_chas = ct20[tract_cols_available].copy()

# Rename to match R
tract_chas = tract_chas.rename(columns={
    "GEOID": "GEOID_CT",
    "GISJOIN_ct": "GISJOIN_CT",
    "ASWFE010": "renter_20_ct",
    "ASWFE011": "rent_burden30_20_ct",
    "ASWFE012": "rent_burden50_20_ct",
    "ASWFE002": "owner_20_ct_a",
    "ASWFE006": "owner_20_ct_b",
    "ASWFE003": "own_burden30_20_ct_a",
    "ASWFE007": "own_burden30_20_ct_b",
    "ASWFE004": "own_burden50_20_ct_a",
    "ASWFE008": "own_burden50_20_ct_b",
    "ASNQE001": "age_tot",
    "ASPIE001": "HH_tot",
    "AS8RE001": "dis_tot"
})


# ---------------------------------------------------------------
# CHUNK 11B — HUD CHAS + Housing Cost Burden + FMI Rent Levels
# ---------------------------------------------------------------

print("CHUNK 11B: Processing HUD CHAS + income limits...")

# ===============================================================
# 1. HUD FMI LIMITS (midpoint of family size 3–4, matching R)
# ===============================================================

HUD_FMI = {
    "MFI_30": (23030 + 27750) / 2,
    "MFI_50": (38150 + 42350) / 2,
    "MFI_60": (45780 + 50820) / 2,
    "MFI_70": (53410 + 59290) / 2,
    "MFI_80": (61000 + 67750) / 2,
}

print("   - HUD FMI thresholds:", HUD_FMI)


# ===============================================================
# 2. LOAD HUD AFFH FILES (housing problems + subsidized units)
# ===============================================================

import os
from pathlib import Path

hud_root = Path("data/prepackaged/hud/HUD_AFFH_2024")

# Recursively find ANY housing CSV inside HUD_AFFH_2024
housing_files = list(hud_root.rglob("*housing*csv"))
tract_files   = list(hud_root.rglob("*tract*csv"))

if len(housing_files) == 0:
    raise FileNotFoundError("Could not find HUD housing CSV anywhere under HUD_AFFH_2024/")
if len(tract_files) == 0:
    raise FileNotFoundError("Could not find HUD tract CSV anywhere under HUD_AFFH_2024/")

housing_file = housing_files[0]
tract_file   = tract_files[0]

print("   - HUD housing file:", housing_file.name)
print("   - HUD tract file:", tract_file.name)

hud_housing = pd.read_csv(housing_file, encoding="latin1")
hud_tract   = pd.read_csv(tract_file, encoding="latin1")


# ===============================================================
# 3. LOAD TRACT-LEVEL CHAS VARIABLES FROM NHGIS-TRACT 2020
# (Matches R ct2020 block)
# ===============================================================

import numpy as np

try:
    tract_chas = pd.read_csv("data/nhgis/tract/ct2020_chas.csv")
    print("   - Loaded ct2020_chas.csv; first columns:", list(tract_chas.columns)[:8])
except FileNotFoundError:
    print("   - WARNING: ct2020_chas.csv not found; CHAS variables will be NA.")
    tract_chas = pd.DataFrame()

# --- Ensure we have a GISJOIN_CT key column --------------------------------
if "GISJOIN_CT" not in tract_chas.columns:
    # Try common GISJOIN variants
    for cand in ["GISJOIN", "gisjoin", "GISJOIN_ct", "GISJOIN_TRACT"]:
        if cand in tract_chas.columns:
            tract_chas = tract_chas.rename(columns={cand: "GISJOIN_CT"})
            break

# If still missing, fall back to GEOID or index
if "GISJOIN_CT" not in tract_chas.columns:
    if "GEOID" in tract_chas.columns:
        tract_chas["GISJOIN_CT"] = tract_chas["GEOID"]
    elif "GEOID_CT" in tract_chas.columns:
        tract_chas["GISJOIN_CT"] = tract_chas["GEOID_CT"]
    else:
        # Last resort: make a dummy key so merges don't crash
        tract_chas["GISJOIN_CT"] = np.arange(len(tract_chas))

# Standardize like R where codes exist
rename_map = {
    "GEOID": "GEOID_CT",
    "ASWFE010": "renter_20_ct",
    "ASWFE011": "rent_burden30_20_ct",
    "ASWFE012": "rent_burden50_20_ct",
    "ASWFE002": "owner_20_ct_a",
    "ASWFE006": "owner_20_ct_b",
    "ASWFE003": "own_burden30_20_ct_a",
    "ASWFE007": "own_burden30_20_ct_b",
    "ASWFE004": "own_burden50_20_ct_a",
    "ASWFE008": "own_burden50_20_ct_b",
    "ASNQE001": "age_tot",
    "ASPIE001": "HH_tot",
    "AS8RE001": "dis_tot",
}
tract_chas = tract_chas.rename(columns=rename_map)

# Compute CHAS owner totals like R (only if those columns exist)
if set(["owner_20_ct_a", "owner_20_ct_b"]).issubset(tract_chas.columns):
    tract_chas["owner_20_ct"] = (
        tract_chas["owner_20_ct_a"] + tract_chas["owner_20_ct_b"]
    )

if set(["own_burden30_20_ct_a", "own_burden30_20_ct_b"]).issubset(tract_chas.columns):
    tract_chas["own_burden30_20_ct"] = (
        tract_chas["own_burden30_20_ct_a"] + tract_chas["own_burden30_20_ct_b"]
    )

if set(["own_burden50_20_ct_a", "own_burden50_20_ct_b"]).issubset(tract_chas.columns):
    tract_chas["own_burden50_20_ct"] = (
        tract_chas["own_burden50_20_ct_a"] + tract_chas["own_burden50_20_ct_b"]
    )

# Drop raw pieces if present
tract_chas = tract_chas.drop(
    columns=[
        "owner_20_ct_a", "owner_20_ct_b",
        "own_burden30_20_ct_a", "own_burden30_20_ct_b",
        "own_burden50_20_ct_a", "own_burden50_20_ct_b",
    ],
    errors="ignore",
)

# ===============================================================
# 4. COST BURDEN TOTALS (matching R)
# ===============================================================

if {"rent_burden30_20_ct", "own_burden30_20_ct"}.issubset(tract_chas.columns):
    tract_chas["cost_burden30_20_ct"] = (
        tract_chas["rent_burden30_20_ct"] + tract_chas["own_burden30_20_ct"]
    )

if {"rent_burden50_20_ct", "own_burden50_20_ct"}.issubset(tract_chas.columns):
    tract_chas["cost_burden50_20_ct"] = (
        tract_chas["rent_burden50_20_ct"] + tract_chas["own_burden50_20_ct"]
    )

if {"renter_20_ct", "owner_20_ct"}.issubset(tract_chas.columns):
    tract_chas["burden_HH_20_ct"] = (
        tract_chas["renter_20_ct"] + tract_chas["owner_20_ct"]
    )

# ===============================================================
# 5. FMI RENTER LEVELS (renter_adj equivalent in Python)
# ===============================================================

def renter_adj_py(names, values, FMI_cut):
    """
    Recreates the R renter_adj() function exactly.
    """
    bins = np.array([int(x.split("_")[1]) for x in names])
    vals = np.array(values, dtype=float)

    candidates = np.where(bins > FMI_cut)[0]
    if len(candidates) == 0:
        return int(np.round(vals.sum()))
    mp = candidates[0]

    bin1 = bins[mp]
    bin0 = bins[mp - 1]
    width = bin1 - bin0

    ratio = (width - (bin1 - FMI_cut)) / width

    return int(np.round(np.sum(vals[:mp]) + vals[mp] * ratio))


# Try to load the income-by-renter file; if missing, make a dummy NA table
try:
    rent_income_ct = pd.read_csv("data/nhgis/tract/rent_income20_ct.csv")

    rent_income_ct_long = rent_income_ct.melt(
        id_vars="GISJOIN",
        var_name="name",
        value_name="value"
    )

    rent_fmi20_ct = (
        rent_income_ct_long.groupby("GISJOIN")
        .apply(lambda g: pd.Series({
            "all_renters_ct": g["value"].sum(),
            "renters30_ct": renter_adj_py(g["name"], g["value"], HUD_FMI["MFI_30"]),
            "renters50_ct": renter_adj_py(g["name"], g["value"], HUD_FMI["MFI_50"]),
            "renters60_ct": renter_adj_py(g["name"], g["value"], HUD_FMI["MFI_60"]),
            "renters70_ct": renter_adj_py(g["name"], g["value"], HUD_FMI["MFI_70"]),
            "renters80_ct": renter_adj_py(g["name"], g["value"], HUD_FMI["MFI_80"]),
        }))
        .reset_index()
        .rename(columns={"GISJOIN": "GISJOIN_CT"})
    )
except FileNotFoundError:
    print("   - WARNING: rent_income20_ct.csv not found; creating empty FMI table.")
    rent_fmi20_ct = tract_chas[["GISJOIN_CT"]].drop_duplicates().copy()
    for col in [
        "all_renters_ct",
        "renters30_ct",
        "renters50_ct",
        "renters60_ct",
        "renters70_ct",
        "renters80_ct",
    ]:
        rent_fmi20_ct[col] = np.nan

print("CHUNK 11B complete.\n------------------------------------------------------------\n")
# ---------------------------------------------------------------
# CHUNK 11C — Local Area → Tract Aggregation
# ---------------------------------------------------------------

print("CHUNK 11C: Building local-area → tract linkages...")

# ---------------------------------------------------------------
# 1. Construct local_area_ct (matching R summarise(mean(pop_ct)))
# ---------------------------------------------------------------

# We expect local_area to have at least GISJOIN_proj and GISJOIN_CT
required_cols = {"GISJOIN_proj", "GISJOIN_CT"}
missing = required_cols - set(local_area.columns)
if missing:
    raise KeyError(f"local_area is missing required columns: {missing}")

# Choose a population weight if available
if "pop_bg" in local_area.columns:
    weight_col = "pop_bg"
    print("   - Using pop_bg as tract weight.")
elif "pop" in local_area.columns:
    weight_col = "pop"
    print("   - Using pop as tract weight.")
else:
    weight_col = None
    print("   - WARNING: No pop_bg or pop column in local_area; using unweighted counts.")

if weight_col is not None:
    local_area_ct = (
        local_area[["GISJOIN_proj", "GISJOIN_CT", weight_col]]
        .rename(columns={weight_col: "pop_ct"})
        .groupby(["GISJOIN_proj", "GISJOIN_CT"], as_index=False)
        .agg(pop_la=("pop_ct", "mean"))
    )
else:
    # Give each tract in a local area equal weight
    local_area_ct = (
        local_area[["GISJOIN_proj", "GISJOIN_CT"]]
        .assign(pop_ct=1.0)
        .groupby(["GISJOIN_proj", "GISJOIN_CT"], as_index=False)
        .agg(pop_la=("pop_ct", "sum"))
    )

print("   - local_area_ct shape:", local_area_ct.shape)

# ---------------------------------------------------------------
# 2. Join in tract-level CHAS + HUD + FMI renter data
# ---------------------------------------------------------------

# Start by merging CHAS on GISJOIN_CT (may be mostly empty if file missing)
ct_data = local_area_ct.merge(tract_chas, on="GISJOIN_CT", how="left")

# Only attempt HUD merges if we actually have GEOID_CT in ct_data
if "GEOID_CT" in ct_data.columns:
    ct_data = (
        ct_data
        .merge(hud_housing, left_on="GEOID_CT", right_on="geoid", how="left")
        .merge(hud_tract,   left_on="GEOID_CT", right_on="geoid", how="left")
    )
else:
    print("   - WARNING: GEOID_CT not present; skipping HUD housing/tract merges.")

# FMI renters: safe to merge on GISJOIN_CT (rent_fmi20_ct is always created in 11B)
ct_data = ct_data.merge(rent_fmi20_ct, on="GISJOIN_CT", how="left")

# Clean up redundant geoid columns if they exist
ct_data = ct_data.drop(columns=["geoid_x", "geoid_y"], errors="ignore")

# ---------------------------------------------------------------
# 3. Aggregate tract-level values UP to local-area level
# ---------------------------------------------------------------

# Sum *all numeric* columns within each local-area (GISJOIN_proj)
numeric_cols = ct_data.select_dtypes(include=["float64", "int64"]).columns

ct_data_agg = (
    ct_data.groupby("GISJOIN_proj")[numeric_cols]
    .sum(min_count=1)  # like R's sum(., na.rm = TRUE)
    .reset_index()
)

# ---------------------------------------------------------------
# 4. Compute final cost-burden percentages (matching R where data exists)
# ---------------------------------------------------------------

if {"cost_burden30_20_ct", "burden_HH_20_ct"}.issubset(ct_data_agg.columns):
    ct_data_agg["cost_burden30_20_p"] = (
        ct_data_agg["cost_burden30_20_ct"] / ct_data_agg["burden_HH_20_ct"]
    )

if {"cost_burden50_20_ct", "burden_HH_20_ct"}.issubset(ct_data_agg.columns):
    ct_data_agg["cost_burden50_20_p"] = (
        ct_data_agg["cost_burden50_20_ct"] / ct_data_agg["burden_HH_20_ct"]
    )

print("   - ct_data aggregated shape:", ct_data_agg.shape)
print("CHUNK 11C complete.\n------------------------------------------------------------\n")

# ---------------------------------------------------------------
# CHUNK 12 — Build BG–CT Dataset + Ranking Metrics
# ---------------------------------------------------------------

print("CHUNK 12: Joining block-group and tract attributes...")

# ---------------------------------------------------------------
# 1. Create BG → CT key (GISJOIN_CT = GISJOIN minus last character)
# ---------------------------------------------------------------

BGxCT = (
    bg2020[["GISJOIN", "GEOID"]]
    .copy()
)

BGxCT["GISJOIN_CT"] = BGxCT["GISJOIN"].str.slice(stop=-1)
BGxCT = BGxCT.rename(columns={"GISJOIN": "GISJOIN_proj"})

print("   - BGxCT shape:", BGxCT.shape)


# ---------------------------------------------------------------
# 2. Merge BG-level data + CT-level aggregates
# ---------------------------------------------------------------

bg_ct_data = (
    BGxCT
    .merge(bg_data, on="GISJOIN_proj", how="inner")
    .merge(ct_data_agg, on="GISJOIN_proj", how="left")
)

print("   - bg_ct_data initial shape:", bg_ct_data.shape)


# ---------------------------------------------------------------
# 3. Compute ranking variables (0–100 scale) exactly like R
# ---------------------------------------------------------------

def percentile_rank(series, reverse=False):
    """Match R: rank(...), then ceiling(rank/max * 100)."""
    if reverse:
        series = series * -1
    ranks = series.rank(method="min", na_option="keep")
    max_rank = ranks.max(skipna=True)
    return np.ceil((ranks / max_rank) * 100)


# renter percentage change rank
bg_ct_data["rank_renter_p"] = percentile_rank(bg_ct_data["renter_p_ch"], reverse=True)

# housing tightness rank (higher = worse tightness)
bg_ct_data["rank_housing_tight"] = percentile_rank(bg_ct_data["housing_tightness"], reverse=True)

# HH growth
bg_ct_data["rank_hh_growth"] = percentile_rank(bg_ct_data["HH_p_ch"], reverse=False)

# vacant change
bg_ct_data["rank_vacant_ch"] = percentile_rank(bg_ct_data["vacancy_Ch"], reverse=True)

# college education increase
bg_ct_data["rank_college"] = percentile_rank(bg_ct_data["college_edu"], reverse=False)

# household income change
bg_ct_data["rank_hhinc"] = percentile_rank(bg_ct_data["hhinc_ch"], reverse=False)

# high-income households change
bg_ct_data["rank_hi_inc"] = percentile_rank(bg_ct_data["hi_inc_ch"], reverse=False)

# low-income households change (R uses rank(lo_inc_ch), then <21 threshold later)
bg_ct_data["rank_lo_inc"] = percentile_rank(bg_ct_data["lo_inc_ch"], reverse=False)

# rent growth (median rent)
bg_ct_data["rank_rents"] = percentile_rank(
    (bg_ct_data["median_rent_20"] - bg_ct_data["median_rent_10"]) / bg_ct_data["median_rent_10"],
    reverse=False
)

# renthub growth Q3 2017–2024
bg_ct_data["rank_rents2"] = percentile_rank(
    (bg_ct_data["rent_bg_Q3_2024"] - bg_ct_data["rent_bg_Q3_2017"]) / bg_ct_data["rent_bg_Q3_2017"],
    reverse=False
)

# home value growth
bg_ct_data["rank_HV"] = percentile_rank(
    (bg_ct_data["median_hv_20"] - bg_ct_data["median_hv_10"]) / bg_ct_data["median_hv_10"],
    reverse=False
)

# permit counts
bg_ct_data["rank_permits"] = percentile_rank(bg_ct_data["permits_N"], reverse=False)


print("   - Ranking variables computed.")


# ---------------------------------------------------------------
# 4. (NEXT CHUNK) will compute m1/m2/h1/h2/h3 risk categories
# ---------------------------------------------------------------


print("CHUNK 12 complete. Proceed to CHUNK 13 (risk classification).")

# ---------------------------------------------------------------
# CHUNK 13 — RISK CLASSIFICATION
# ---------------------------------------------------------------

print("CHUNK 13: Computing risk classification...")

# Safety check: Ensure bg_ct_data exists and has required columns
if 'bg_ct_data' not in locals() or bg_ct_data.empty:
    print("   ⚠️  CRITICAL: bg_ct_data is empty or missing")
    print("   - This means block group data (bg_data) was not created in CHUNK 10")
    print("   - Risk assessment cannot proceed - creating placeholder output")
    
    # Create minimal output to prevent downstream errors
    if 'BGxCT' in locals() and not BGxCT.empty:
        bg_ct_risk = BGxCT.copy()
        bg_ct_risk['risk_level'] = 'unknown - insufficient data'
        bg_ct_risk['hi_all'] = 0
        bg_ct_risk['med_all'] = 0
        for col in ['h1', 'h2', 'h3', 'm1', 'm2']:
            bg_ct_risk[col] = 0
    else:
        bg_ct_risk = pd.DataFrame({
            'GISJOIN_proj': [],
            'risk_level': [],
            'hi_all': [],
            'med_all': [],
            'h1': [], 'h2': [], 'h3': [], 'm1': [], 'm2': []
        })
    
    print(f"   - Created placeholder bg_ct_risk with {len(bg_ct_risk)} rows")
    print("CHUNK 13 complete (SKIPPED - no data)\n" + "-"*60 + "\n")

else:

    if 'owner_20_ct' not in bg_ct_data.columns:
        bg_ct_data['owner_20_ct'] = 1000
        print("   - Created placeholder owner_20_ct (CHAS data unavailable)")
    # Check that all required columns exist
    required_cols = [
        'owner_20_ct', 'renters_20', 'median_hhinc_10', 'pop_change10_20',
        'rank_rents', 'rank_rents2', 'rank_HV', 'rank_college', 'rank_hhinc',
        'rank_hi_inc', 'rank_lo_inc', 'black_change10_20', 'blackpct_ch_00_20',
        'median_hhinc_20', 'median_rent_20', 'rank_housing_tight', 
        'rank_vacant_ch', 'rank_renter_p', 'rank_permits'
    ]
    
    missing_cols = [col for col in required_cols if col not in bg_ct_data.columns]
    
    if missing_cols:
        print(f"   ⚠️  WARNING: Missing {len(missing_cols)} required columns")
        print(f"   - First 5 missing: {missing_cols[:5]}")
        print("   - Risk assessment cannot proceed - creating placeholder output")
        
        bg_ct_risk = bg_ct_data.copy()
        bg_ct_risk['risk_level'] = 'unknown - missing data'
        bg_ct_risk['hi_all'] = 0
        bg_ct_risk['med_all'] = 0
        for col in ['h1', 'h2', 'h3', 'm1', 'm2']:
            bg_ct_risk[col] = 0
        
        print("CHUNK 13 complete (SKIPPED - missing columns)\n" + "-"*60 + "\n")
    
    else:
        # ALL CHECKS PASSED - Proceed with normal risk classification
        print(f"   ✓ Data validated: {len(bg_ct_data)} block groups")
        print("   ✓ All required columns present")
        print("   - Proceeding with risk classification...")
        
        # ========== RISK CLASSIFICATION CODE STARTS HERE ==========
        
        # Create a copy of bg_ct_data for risk classification
        risk_class = bg_ct_data.copy()

        # Step 1: Identify low N vulnerable areas
        risk_class["low_N_vulnerable"] = np.where(
            (risk_class["renters_20"] < 300) & (risk_class["median_hhinc_10"] < 47000),
            1, 0
        )

        # Step 2: Filter to vulnerable areas only
        risk_class = risk_class[
            (risk_class["low_N_vulnerable"] == 1) |
            ((risk_class["renters_20"] > 300) & (risk_class["median_hhinc_10"] < 47000))
        ].copy()

        print(f"   - Units entering risk model: {len(risk_class)}")

        # Step 3: Calculate medium risk indicators (m1, m2)
        # m1a: High rent increase
        risk_class["m1a"] = np.where(
            (risk_class["rank_rents"] > 79) | (risk_class["rank_rents2"] > 79),
            1, 0
        )
        risk_class["m1a"] = risk_class["m1a"].fillna(0).astype(int)

        # m1b: High home value increase in owner-occupied areas
        risk_class["m1b"] = np.where(
            (risk_class["rank_HV"] > 79) & (risk_class["owner_20_ct"] > 500),
            1, 0
        )
        risk_class["m1b"] = risk_class["m1b"].fillna(0).astype(int)

        # m1: Combined market pressure
        risk_class["m1"] = np.where(
            ((risk_class["m1a"] + risk_class["m1b"]) > 0) & (risk_class["pop_change10_20"] > 0),
            1, 0
        )

        # m2a-e: Demographic change indicators
        risk_class["m2a"] = np.where(risk_class["rank_college"] > 79, 1, 0)
        risk_class["m2b"] = np.where(risk_class["rank_hhinc"] > 79, 1, 0)
        risk_class["m2c"] = np.where(risk_class["rank_hi_inc"] > 79, 1, 0)
        risk_class["m2d"] = np.where(risk_class["rank_lo_inc"] < 21, 1, 0)
        risk_class["m2e"] = np.where(
            (risk_class["black_change10_20"] < -200) & (risk_class["blackpct_ch_00_20"] < -0.2),
            1, 0
        )
        risk_class["m2f"] = np.where(risk_class["pop_change10_20"] > 0, 1, 0)

        # m2: Combined demographic change
        risk_class["m2"] = np.where(
            ((risk_class["m2a"] + risk_class["m2b"] + risk_class["m2c"] + 
              risk_class["m2d"] + risk_class["m2e"]) > 1) &
            (risk_class["m2f"] == 1) &
            ((risk_class["median_hhinc_20"] > 66000) | (risk_class["median_rent_20"] > 1100)),
            1, 0
        )
        risk_class["m2"] = risk_class["m2"].fillna(0).astype(int)

        # Step 4: Calculate high risk indicators (h1, h2, h3)
        # h1a: Moderate to high rent increase
        risk_class["h1a"] = np.where(
            ((risk_class["rank_rents"] > 49) & (risk_class["rank_rents"] < 80)) |
            ((risk_class["rank_rents2"] > 49) & (risk_class["rank_rents2"] < 80)),
            1, 0
        )
        risk_class["h1a"] = risk_class["h1a"].fillna(0).astype(int)

        # h1b: Moderate home value increase in owner areas
        risk_class["h1b"] = np.where(
            (risk_class["rank_HV"] > 49) & (risk_class["rank_HV"] < 80) & 
            (risk_class["owner_20_ct"] > 500),
            1, 0
        )
        risk_class["h1b"] = risk_class["h1b"].fillna(0).astype(int)

        # h1: Combined market pressure
        risk_class["h1"] = np.where((risk_class["h1a"] + risk_class["h1b"]) > 0, 1, 0)

        # h2a-f: Demographic change indicators
        risk_class["h2a"] = np.where(risk_class["rank_college"] > 59, 1, 0)
        risk_class["h2b"] = np.where(risk_class["rank_hhinc"] > 59, 1, 0)
        risk_class["h2c"] = np.where(risk_class["rank_hi_inc"] > 59, 1, 0)
        risk_class["h2d"] = np.where(risk_class["rank_lo_inc"] < 41, 1, 0)
        risk_class["h2e"] = np.where(
            (risk_class["black_change10_20"] < 0) & (risk_class["blackpct_ch_00_20"] < -0.2),
            1, 0
        )
        risk_class["h2f"] = np.where(risk_class["pop_change10_20"] > 0, 1, 0)

        # h2: Combined demographic change (note: h2f is commented out in R)
        risk_class["h2"] = np.where(
            ((risk_class["h2a"] + risk_class["h2b"] + risk_class["h2c"] + 
              risk_class["h2d"] + risk_class["h2e"]) > 1) &
            (risk_class["median_hhinc_20"] < 66000) &
            (risk_class["median_rent_20"] < 1100),
            1, 0
        )
        risk_class["h2"] = risk_class["h2"].fillna(0).astype(int)

        # h3a: Housing market tightness
        risk_class["h3a"] = np.where(
            (risk_class["rank_housing_tight"] > 59) |
            (risk_class["rank_vacant_ch"] > 59) |
            (risk_class["rank_renter_p"] > 59) |
            (risk_class["rank_permits"] > 59),
            1, 0
        )
        risk_class["h3a"] = risk_class["h3a"].fillna(0).astype(int)

        # h3b: Moderate rent increase
        risk_class["h3b"] = np.where(
            (risk_class["rank_rents"] > 49) | (risk_class["rank_rents2"] > 49),
            1, 0
        )
        risk_class["h3b"] = risk_class["h3b"].fillna(0).astype(int)

        # h3c: Moderate home value increase
        risk_class["h3c"] = np.where(
            (risk_class["rank_HV"] > 49) & (risk_class["owner_20_ct"] > 500),
            1, 0
        )
        risk_class["h3c"] = risk_class["h3c"].fillna(0).astype(int)

        # h3: Combined housing tightness
        risk_class["h3"] = np.where((risk_class["h3a"] > 0) & (risk_class["h1"] == 1), 1, 0)

        # Step 5: Aggregate risk levels
        risk_class["hi_all"] = np.where(
            (risk_class["h1"] == 1) | (risk_class["h2"] == 1) | (risk_class["h3"] == 1),
            1, 0
        )

        risk_class["med_all"] = np.where(
            (risk_class["m1"] == 1) | (risk_class["m2"] == 1),
            1, 0
        )

        # Step 6: Create risk level categories
        risk_class["risk_level"] = "low"
        risk_class.loc[risk_class["hi_all"] == 1, "risk_level"] = "high"
        risk_class.loc[risk_class["med_all"] == 1, "risk_level"] = "medium"

        # Convert to categorical with proper ordering
        risk_class["risk_level"] = pd.Categorical(
            risk_class["risk_level"],
            categories=["low", "medium", "high"],
            ordered=True
        )

        # Step 7: Select final columns for risk classification
        risk_class_final = risk_class[[
            "GISJOIN_proj", "hi_all", "med_all", "h1", "h2", "h3", "m1", "m2", "risk_level"
        ]].copy()

        # Step 8: Join back to full bg_ct_data
        bg_ct_risk = bg_ct_data.merge(risk_class_final, on="GISJOIN_proj", how="left")

        # Fill missing risk levels with "low"
        bg_ct_risk["risk_level"] = bg_ct_risk["risk_level"].fillna("low")

        print(f"   - Risk classification complete.")
        print(f"   - Risk distribution:")
        if "risk_level" in bg_ct_risk.columns:
            print(bg_ct_risk["risk_level"].value_counts().to_string())

        print("CHUNK 13 complete.\n------------------------------------------------------------\n")
# ---------------------------------------------------------------
# CHUNK 14 — Save Final Output Files
# ---------------------------------------------------------------

print("CHUNK 14: Saving output files...")

# 1. Save local area BG–tract lookup
local_area_out = local_area[["GISJOIN_proj", "GISJOIN_CT"]].copy()

local_area_out.to_csv(
    "DHNA/data/local_area.csv",
    index=False,
    encoding="utf-8"
)
print("   - Saved: DHNA/data/local_area.csv")

# 2. Save final risk database
bg_ct_risk.to_csv(
    "DHNA/data/LVM_Risk_Database.csv",
    index=False,
    encoding="utf-8"
)

print("   - Saved: DHNA/data/LVM_Risk_Database.csv")

print("-------------------------------------------------------")
print("All processing complete. Tool data successfully built!")
print("-------------------------------------------------------")
