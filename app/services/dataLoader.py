from supabase import create_client, Client
import pandas as pd
import geopandas as gpd
import tempfile
from pathlib import Path
from io import StringIO
import os
from dotenv import load_dotenv

load_dotenv()

# setup - defer client creation to avoid import-time errors
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = None  # Will be created on first use

BUCKET_NAME = "dhna-output-data"

# all csv are directly loaded into dictionary of dataframes (refer to comments at bottom)
def load_all_csvs() -> dict:
    """Load all CSV files from bucket directly into memory"""
    global supabase
    
    # Apply httpx monkeypatch before creating Supabase client
    import httpx
    if not hasattr(httpx.Client.__init__, '_patched'):
        _original_httpx_init = httpx.Client.__init__
        
        def _patched_httpx_init(self, *args, **kwargs):
            kwargs.pop('proxy', None)
            return _original_httpx_init(self, *args, **kwargs)
        
        _patched_httpx_init._patched = True
        httpx.Client.__init__ = _patched_httpx_init
    
    # Create client on first use
    if supabase is None:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    datasets = {}
    
    try:
        files = supabase.storage.from_(BUCKET_NAME).list()
        print(f"Loading CSV files from bucket: {BUCKET_NAME}\n")
        
        for file in files:
            if file.get('id') and file['name'].endswith('.csv'):
                file_name = file['name']
                try:
                    csv_bytes = supabase.storage.from_(BUCKET_NAME).download(file_name)
                    csv_string = csv_bytes.decode('utf-8')
                    df = pd.read_csv(StringIO(csv_string))
                    datasets[file_name] = df
                    print(f"✅ {file_name}: {df.shape[0]} rows × {df.shape[1]} columns")
                except Exception as e:
                    print(f"❌ Failed to load {file_name}: {e}")
        
        print(f"\n{'='*50}")
        print(f"✅ Loaded {len(datasets)} CSV files into memory")
        print(f"{'='*50}")
        return datasets
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {}


def load_shapefile() -> gpd.GeoDataFrame:
    """Load the KY_Jefferson_BG_2023 shapefile from Supabase into memory"""
    global supabase
    
    # Create client on first use
    if supabase is None:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    shapefile_name = "KY_Jefferson_BG_2023.shp"
    companion_files = ["KY_Jefferson_BG_2023.shx", "KY_Jefferson_BG_2023.dbf", "KY_Jefferson_BG_2023.prj"]
    
    try:
        # Create temporary directory for shapefile components
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Download main shapefile
            print(f"Loading shapefile from bucket: {BUCKET_NAME}")
            shp_data = supabase.storage.from_(BUCKET_NAME).download(shapefile_name)
            shp_file = temp_path / shapefile_name
            shp_file.write_bytes(shp_data)
            print(f"✅ Downloaded {shapefile_name}")
            
            # Download companion files
            for companion in companion_files:
                try:
                    companion_data = supabase.storage.from_(BUCKET_NAME).download(companion)
                    companion_file = temp_path / companion
                    companion_file.write_bytes(companion_data)
                    print(f"✅ Downloaded {companion}")
                except Exception as e:
                    print(f"⚠️  Could not download {companion}: {e}")
            
            # Load shapefile with geopandas (don't transform CRS yet - that happens after filtering)
            gdf = gpd.read_file(str(shp_file))
            print(f"✅ Shapefile loaded: {len(gdf)} features × {len(gdf.columns)} columns")
            return gdf
            
    except Exception as e:
        print(f"❌ Failed to load shapefile: {e}")
        raise

# run
if __name__ == "__main__":
    datasets = load_all_csvs()
    
# Dictionary keys (filenames) and their contents:
# 'local_area.csv' - Census tract relationships to block groups
# 'LVM_Risk_Database.csv' - Risk assessment data with 105 indicators
# 'pop_ethnorace.csv' - Population by ethnicity/race over time
# 'Renthub_quarterly_rent.csv' - Quarterly rent data by geography