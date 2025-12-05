from supabase import create_client, Client
import pandas as pd
from io import StringIO
import os
from dotenv import load_dotenv

load_dotenv()

# setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BUCKET_NAME = "dhna-output-data"

# all csv are directly loaded into dictionary of dataframes (refer to comments at bottom)
def load_all_csvs() -> dict:
    """Load all CSV files from bucket directly into memory"""
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

# run
if __name__ == "__main__":
    datasets = load_all_csvs()
    
# Dictionary keys (filenames) and their contents:
# 'local_area.csv' - Census tract relationships to block groups
# 'LVM_Risk_Database.csv' - Risk assessment data with 105 indicators
# 'pop_ethnorace.csv' - Population by ethnicity/race over time
# 'Renthub_quarterly_rent.csv' - Quarterly rent data by geography