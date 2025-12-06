from dotenv import load_dotenv
import os

# Load .env
load_dotenv()

# Read variables
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
schema = os.getenv("SUPABASE_SCHEMA", "public")

print("SUPABASE_URL:", url)
print("SUPABASE_SERVICE_ROLE_KEY:", "SET" if key else "NOT SET")
print("SUPABASE_SCHEMA:", schema)
