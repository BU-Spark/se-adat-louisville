# ETL Data Pipeline

Processes NHGIS census data to generate displacement risk assessments for Louisville Metro.

## Quick Start
```bash
pip install pandas geopandas numpy shapely supabase python-dotenv
python pipeline/main_pipeline.py
```

## What It Does

1. Loads census data (1990-2020) from `data/nhgis/`
2. Crosswalks to 2020 geography and standardizes
3. Calculates displacement risk using 14 indicators
4. Outputs to `DHNA/data/` and uploads to Supabase

## Outputs

- `LVM_Risk_Database.csv` - Risk assessments (high/medium/low)
- `pop_ethnorace.csv` - Population demographics
- `local_area.csv` - Area definitions
- `Renthub_quarterly_rent.csv` - Rent trends

## Environment Variables
```env
SUPABASE_URL=your_url
SUPABASE_KEY=your_key
```

## Key Algorithms

- **Median interpolation**: Estimates medians from binned census data
- **Risk scoring**: Multi-indicator system for market pressure, demographic change, and housing tightness
- **Spatial aggregation**: 800m proximity-based local areas

## Troubleshooting

- Missing data: Ensure NHGIS files are in `data/nhgis/` subdirectories
- Supabase errors: Verify bucket `dhna-output-data` exists
- Memory: Requires 4GB+ RAM