import pandas as pd
import os
from typing import Optional, Dict, Any

def diagnose_sector_data(csv_path: str = "./data/LVM_Risk_Database.csv") -> Dict[str, Any]:
    """
    Diagnose the geographic identifier columns in the risk database
    
    Returns information about:
    - Available identifier columns (GISJOIN, GISJOIN_proj, bgid, etc.)
    - Sample values from each column
    - Data types and unique counts
    """
    
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        return {"error": f"File not found: {csv_path}"}
    except Exception as e:
        return {"error": f"Error loading file: {e}"}
    
    # Find all potential identifier columns
    id_columns = [col for col in df.columns if any(
        keyword in col.lower() 
        for keyword in ['gis', 'join', 'bgid', 'geoid', 'tract', 'block']
    )]
    
    results = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "all_columns": list(df.columns),
        "identifier_columns": {},
    }
    
    # Analyze each identifier column
    for col in id_columns:
        col_info = {
            "dtype": str(df[col].dtype),
            "unique_count": df[col].nunique(),
            "null_count": df[col].isnull().sum(),
            "sample_values": df[col].dropna().head(5).tolist(),
        }
        results["identifier_columns"][col] = col_info
    
    # Check if any standard identifier exists
    standard_ids = ["GISJOIN", "GISJOIN_proj", "bgid", "GEOID"]
    results["available_standard_ids"] = [id_col for id_col in standard_ids if id_col in df.columns]
    
    return results


def test_sector_lookup(
    bgid_value: str,
    csv_path: str = "./data/LVM_Risk_Database.csv",
    search_columns: Optional[list] = None
) -> Dict[str, Any]:
    """
    Test if a specific bgid value can be found in the database
    
    Args:
        bgid_value: The geographic identifier to search for
        csv_path: Path to the risk database CSV
        search_columns: List of columns to search in (if None, tries common ones)
    
    Returns:
        Dictionary with search results
    """
    
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        return {"error": f"Error loading file: {e}"}
    
    if search_columns is None:
        # Default columns to search
        search_columns = [col for col in df.columns if any(
            keyword in col.lower() 
            for keyword in ['gis', 'join', 'bgid', 'geoid']
        )]
    
    results = {
        "search_value": bgid_value,
        "matches": {}
    }
    
    for col in search_columns:
        if col not in df.columns:
            continue
            
        # Try exact match
        exact_match = df[df[col] == bgid_value]
        if not exact_match.empty:
            results["matches"][col] = {
                "match_type": "exact",
                "row_count": len(exact_match),
                "sample_row": exact_match.iloc[0].to_dict()
            }
        else:
            # Try string conversion match (in case of type mismatch)
            try:
                str_match = df[df[col].astype(str) == str(bgid_value)]
                if not str_match.empty:
                    results["matches"][col] = {
                        "match_type": "string_converted",
                        "row_count": len(str_match),
                        "sample_row": str_match.iloc[0].to_dict()
                    }
            except:
                pass
    
    if not results["matches"]:
        results["error"] = f"No matches found for '{bgid_value}' in any identifier column"
        results["suggestion"] = "Try running diagnose_sector_data() to see available identifiers"
    
    return results


def print_diagnostic_report(csv_path: str = "./data/LVM_Risk_Database.csv"):
    """Print a formatted diagnostic report"""
    
    print("=" * 80)
    print("SECTOR DATA DIAGNOSTIC REPORT")
    print("=" * 80)
    
    results = diagnose_sector_data(csv_path)
    
    if "error" in results:
        print(f"\n❌ ERROR: {results['error']}")
        return
    
    print(f"\n📊 Database Overview:")
    print(f"   Total rows: {results['total_rows']:,}")
    print(f"   Total columns: {results['total_columns']}")
    
    print(f"\n🔑 Available Standard Identifiers:")
    if results["available_standard_ids"]:
        for id_col in results["available_standard_ids"]:
            print(f"   ✓ {id_col}")
    else:
        print("   ⚠️  No standard identifiers found (GISJOIN, GISJOIN_proj, bgid, GEOID)")
    
    print(f"\n🗺️  All Identifier Columns Found:")
    if results["identifier_columns"]:
        for col, info in results["identifier_columns"].items():
            print(f"\n   Column: {col}")
            print(f"      Type: {info['dtype']}")
            print(f"      Unique values: {info['unique_count']:,}")
            print(f"      Null values: {info['null_count']}")
            print(f"      Sample values: {info['sample_values'][:3]}")
    else:
        print("   ⚠️  No identifier columns found")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS:")
    print("=" * 80)
    
    if "GISJOIN_proj" in results["available_standard_ids"]:
        print("✓ GISJOIN_proj found - this is likely the correct column to use for bgid lookup")
    elif "GISJOIN" in results["available_standard_ids"]:
        print("⚠️  GISJOIN found but not GISJOIN_proj - you may need to use GISJOIN instead")
    else:
        print("❌ Neither GISJOIN nor GISJOIN_proj found")
        print("   You may need to:")
        print("   1. Check if the column has a different name")
        print("   2. Verify you're using the correct CSV file")
        print("   3. Check if data preprocessing is needed")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = "./data/LVM_Risk_Database.csv"
    
    print_diagnostic_report(csv_path)
    
    # If a test bgid is provided, test the lookup
    if len(sys.argv) > 2:
        test_bgid = sys.argv[2]
        print(f"\n\n{'='*80}")
        print(f"TESTING LOOKUP FOR: {test_bgid}")
        print("=" * 80)
        
        result = test_sector_lookup(test_bgid, csv_path)
        
        if "error" in result:
            print(f"\n❌ {result['error']}")
            if "suggestion" in result:
                print(f"💡 {result['suggestion']}")
        else:
            print(f"\n✓ Found {len(result['matches'])} matching column(s):")
            for col, match_info in result["matches"].items():
                print(f"\n   Column: {col}")
                print(f"   Match type: {match_info['match_type']}")
                print(f"   Row count: {match_info['row_count']}")
                print(f"   Risk level: {match_info['sample_row'].get('risk_level', 'N/A')}")
