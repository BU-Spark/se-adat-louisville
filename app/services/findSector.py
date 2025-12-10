"""
bg_id exact equivalent (keeps original R names)

This function reproduces exactly what the bg_id reactive in app.R does:
- It accepts coordinates (lat, lng).
- It uses the same file names / in-memory variable names as the R app:
    - lvm_bg_geo : block-group GeoDataFrame (or will be read from "./data/gis/KY_blck_grp_2022.shp")
    - pop_ethnorace : population DataFrame (or will be read from "./data/pop_ethnorace.csv")
- It applies the same filters/joins the R code uses:
    * filters lvm_bg_geo to COUNTYFP == "111"
    * transforms to EPSG:4326
    * left-joins pop_ethnorace filtered to data_yr == 2020 on GISJOIN_proj,
      then keeps only rows with pop > 0
- It constructs a POINT(long, lat) and computes st_intersects equivalent,
  then returns the GISJOIN of the first intersecting row (or None if NA),
  and prints the 1-based index (or "NA") just like the R code prints 'bg'.

Notes on names and files (kept identical to the R script):
- "./data/gis/KY_blck_grp_2022.shp" : block group shapefile used to produce lvm_bg_geo.
  Required columns:
    - "GISJOIN" (string): block-group id column the app indexes and returns
    - "COUNTYFP" (string): used to filter COUNTYFP == "111"
  Companion shapefile files (.dbf, .shx, .prj, etc.) must be present in the same folder.
- "./data/pop_ethnorace.csv" : population CSV used to build pop_map in the R app.
  Required columns:
    - "GISJOIN_proj" : GISJOIN key used to join to lvm_bg_geo$GISJOIN
    - "data_yr" : numeric year (we filter to 2020)
    - "pop" : numeric population (we filter pop > 0)
  This file is named exactly as in the R script and must be present.

Extra parameters introduced (not in the original R script)
- lvm_bg_geo (optional): if provided, must be a GeoDataFrame already loaded in memory and matching
  the contents of the shapefile. If not provided, the function will read the shapefile path above.
  Purpose: allow calling the function with in-memory data (faster / avoids re-reading disk).
  How assigned/produced: in your Python code you can set
      lvm_bg_geo = geopandas.read_file("./data/gis/KY_blck_grp_2022.shp")
- pop_ethnorace (optional): if provided, should be a pandas.DataFrame (like reading the CSV).
  If absent, the function will read "./data/pop_ethnorace.csv".
  Purpose: same as above.
  How assigned/produced:
      pop_ethnorace = pandas.read_csv("./data/pop_ethnorace.csv")

Return
- string GISJOIN (same value that lvm_bg_geo$GISJOIN[row] would return in R), or
- None when R would have NA (no lat set, or no intersecting polygon after the filters).
- The function prints the same integer that R printed (1-based index) or "NA" when there is no match.

Usage examples:
- Using disk reads (no in-memory inputs):
    gid = bg_id(38.252, -85.755)
- Using in-memory GeoDataFrame / DataFrame:
    import geopandas as gpd, pandas as pd
    lvm_bg_geo = gpd.read_file("KY_Jefferson_BG_2023.shp")
    pop_ethnorace = pd.read_csv("pop_ethnorace.csv")
    gid = bg_id(38.252, -85.755, lvm_bg_geo=lvm_bg_geo, pop_ethnorace=pop_ethnorace)

"""
from typing import Optional
import os
import warnings

import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point


def bg_id(
    lat: float,
    lng: float,
) -> Optional[str]:
    """
    Python equivalent of the bg_id reactive in app.R using identical file names.

    Parameters
    - lat, lng: coordinates in decimal degrees. This mirrors pr_location1()$lat and $lng.
      If lat is None or NaN, the function returns None (R's NA branch).
    - lvm_bg_geo: optional GeoDataFrame. If provided it is used as-is (must contain columns
      "GISJOIN" and possibly "COUNTYFP"). If not provided, this function will attempt to read
      "./data/gis/KY_blck_grp_2022.shp" (identical name used in app.R).
    - pop_ethnorace: optional pandas.DataFrame corresponding to "./data/pop_ethnorace.csv".
      If provided it is used (must have columns "GISJOIN_proj", "data_yr", "pop").
      If not provided, the function will read "./data/pop_ethnorace.csv".
    - data_dir: base directory for the files (default "./data"). This parameter is NOT in the
      original R script; it's included only to control where the function reads the identical
      filenames from. If you prefer, pass preloaded lvm_bg_geo and pop_ethnorace instead.

    Returns
    - GISJOIN string (from the lvm_bg_geo row) or None when R would return NA.
    Side effects:
    - prints the 1-based integer index of the matched row (like the R code's print(bg)),
      or prints "NA" if no match (again matching R).
    """

    # --- mimic R behavior: if lat is NA, R returns NA
    if lat is None:
        print("NA")
        return None
    # treat NaN like NA
    try:
        if isinstance(lat, float) and np.isnan(lat):
            print("NA")
            return None
    except Exception:
        pass

    # --- load lvm_bg_geo from Supabase
    from app.services.dataLoader import load_shapefile
    lvm_bg_geo = load_shapefile()

    # Validate required column existence
    if "GISJOIN" not in lvm_bg_geo.columns:
        raise ValueError("lvm_bg_geo must contain column 'GISJOIN' (same as in R)")

    # --- load pop_ethnorace from existing loaded CSVs
    from app.services.dataLoader import load_all_csvs
    datasets = load_all_csvs()
    pop_ethnorace = datasets.get('pop_ethnorace.csv')
    if pop_ethnorace is None:
        raise FileNotFoundError("pop_ethnorace.csv not found in loaded datasets")

    # Validate pop_ethnorace columns
    for col in ("GISJOIN_proj", "data_yr", "pop"):
        if col not in pop_ethnorace.columns:
            raise ValueError(f"pop_ethnorace must contain column '{col}' (as in the R CSV)")

    # Work on a copy to avoid mutating user objects
    gdf = lvm_bg_geo.copy()

    # --- R code filtered county to COUNTYFP == "111"
    if "COUNTYFP" in gdf.columns:
        gdf = gdf[gdf["COUNTYFP"] == "111"]

    # --- convert CRS to EPSG:4326 (R attempted st_transform(..., crs=4326))
    if gdf.crs is None:
        warnings.warn("lvm_bg_geo has no CRS; proceeding assuming it's already EPSG:4326 (WGS84).")
    else:
        try:
            gdf = gdf.to_crs(epsg=4326)
        except Exception:
            warnings.warn("Failed to transform lvm_bg_geo to EPSG:4326. Proceeding with provided CRS.")

    # --- left join to pop_map (data_yr == 2020) and filter pop > 0, matching R's pop_map logic
    pop_map = pop_ethnorace[pop_ethnorace["data_yr"] == 2020][["GISJOIN_proj", "pop"]]
    # left join: gdf$GISJOIN == pop_map$GISJOIN_proj
    gdf = gdf.merge(pop_map, left_on="GISJOIN", right_on="GISJOIN_proj", how="left")
    gdf = gdf[gdf["pop"] > 0]  # keep only BGs with pop > 0 as in R

    # If no BGs left after filters, R would eventually return NA; print NA like R and return None
    if gdf.empty:
        print("NA")
        return None

    # --- build point as R did: st_point(c(long, lat)) (i.e., Point(lng, lat))
    pt = Point(lng, lat)

    # --- compute intersects across the entire gdf (ensures order is same as original gdf row order)
    # Using vectorized .intersects replicates R's st_intersects behavior for a single point.
    try:
        intersects_series = gdf.geometry.intersects(pt)
    except Exception as e:
        # If geometry operations fail, raise informative error
        raise RuntimeError(f"Geometry intersects failed: {e}")

    # Find matching positions (0-based numpy indices)
    matches_positions = np.flatnonzero(intersects_series.to_numpy())

    # If no matches, R's integer(0)[1] would be NA; print NA and return None to mirror R
    if matches_positions.size == 0:
        print("NA")
        return None

    # R code picks the first matching index (st_intersects(...)[[1]][1]).
    first_pos = int(matches_positions[0])  # 0-based position within gdf

    # Print the 1-based index (R printed bg which is 1-based row number)
    print(first_pos + 1)

    # Return the GISJOIN for that row (same as lvm_bg_geo$GISJOIN[bg] in R)
    gisjoin_value = gdf.iloc[first_pos]["GISJOIN"]

    return gisjoin_value


# Quick demonstration guard (not executed when imported)
if __name__ == "__main__":
    # Example usage (requires the same files present at the same paths used in app.R):
    # gid = bg_id(38.252, -85.755)
    # print("GISJOIN:", gid)
    pass


def geocode_address(address: str, city: str, zipcode: str) -> tuple:
    """
    Geocode an address to latitude and longitude coordinates using Nominatim API.
    
    Args:
        address: Street address (e.g., "Main Street")
        city: City name (e.g., "Louisville")
        zipcode: ZIP code (e.g., "40202")
    
    Returns:
        Tuple of (latitude, longitude) as floats, or (None, None) if geocoding fails
    
    Raises:
        ImportError: If geopy is not installed
    """
    try:
        from geopy.geocoders import Nominatim
    except ImportError:
        raise ImportError("geopy is required for geocoding. Install with: pip install geopy")
    
    try:
        # Create a geocoder instance
        geolocator = Nominatim(user_agent="se-adat-louisville")
        
        # Format the full address
        full_address = f"{address}, {city}, {zipcode}, Kentucky"
        
        # Geocode the address
        location = geolocator.geocode(full_address, timeout=10)
        
        if location is None:
            print(f"Could not geocode address: {full_address}")
            return (None, None)
        
        return (location.latitude, location.longitude)
    
    except Exception as e:
        print(f"Error geocoding address: {e}")
        return (None, None)