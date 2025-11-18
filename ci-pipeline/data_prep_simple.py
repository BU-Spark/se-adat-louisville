"""
Simplified ADAT Data Preparation Module
For CI/CD Pipeline Demonstration
"""

import numpy as np
import re


def med_lin_est(names, values):
    """
    Median linear interpolation function.

    Args:
        names: list of variable names (e.g., ['rent_100','rent_149',...])
        values: list of counts corresponding to bins

    Returns:
        Median estimate as float
    """
    vals = np.array(values, dtype=float)
    if vals.sum() == 0:
        return np.nan

    # Locate bin where cumulative crosses 50%
    cum = vals.cumsum() / vals.sum()
    try:
        mp = np.where(cum > 0.5)[0][0]
    except IndexError:
        return np.nan

    # Extract bin numeric values
    def bin_number(name):
        m = re.search(r"_(\d+)", name)
        return float(m.group(1)) if m else np.nan

    bin_1 = bin_number(names[mp])
    if mp > 0:
        bin_0 = bin_number(names[mp - 1])
        inc_width = bin_1 - bin_0
        inc_ratio = (vals.sum() / 2 - vals[:mp].sum()) / vals[mp]
        return bin_0 + inc_ratio * inc_width

    # If mp == 0 (first bin holds median)
    next_bin = bin_number(names[mp + 1])
    inc_ratio_1 = 0.5 / (vals[0] / vals.sum())
    return next_bin * inc_ratio_1


def renter_adj(names, values, fmi):
    """
    Renter FMI (Family Median Income) cutoff adjustment.

    Args:
        names: list of income bin names
        values: list of counts for each bin
        fmi: family median income threshold

    Returns:
        Adjusted count as integer
    """
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


def calculate_risk_level(median_income, median_rent, rent_change):
    """
    Calculate displacement risk level based on area characteristics.

    Args:
        median_income: median household income
        median_rent: median rent cost
        rent_change: percentage change in rent

    Returns:
        Risk level: 'low', 'medium', or 'high'
    """
    if median_income < 47000:  # Vulnerable threshold
        if rent_change > 0.20:  # 20% increase
            return "high"
        elif rent_change > 0.10:  # 10% increase
            return "medium"
        else:
            return "low"
    return "low"


def validate_project_data(project_data):
    """
    Validate that project data has required fields.

    Args:
        project_data: dictionary with project information

    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    required_fields = ["location", "units", "affordable_units"]

    for field in required_fields:
        if field not in project_data:
            return False, f"Missing required field: {field}"

    if not isinstance(project_data["units"], (int, float)) or project_data["units"] <= 0:
        return False, "Units must be a positive number"

    if (
        not isinstance(project_data["affordable_units"], (int, float))
        or project_data["affordable_units"] < 0
    ):
        return False, "Affordable units must be non-negative"

    if project_data["affordable_units"] > project_data["units"]:
        return False, "Affordable units cannot exceed total units"

    return True, ""


if __name__ == "__main__":
    print("ADAT Data Preparation Module - Simplified Version")
    print("This module contains core functions for the Anti-Displacement Assessment Tool")
