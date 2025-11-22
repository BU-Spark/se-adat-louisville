"""
DHNA Displacement Risk Assessment API - REFERENCE-BASED
FastAPI backend that reads CSV files from Supabase Storage
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv
import io

load_dotenv()

# ============================================================================
# APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="DHNA Displacement Risk API (Reference-Based)",
    description="API for accessing Louisville Metro displacement risk data from cloud storage",
    version="2.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_file_metadata(file_type: str):
    """Get file metadata from database"""
    response = supabase.table('data_files').select('*').eq('file_type', file_type).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail=f"No file found for type: {file_type}")
    return response.data[0]

def download_csv_from_storage(bucket_path: str) -> pd.DataFrame:
    """Download and parse CSV from Supabase storage"""
    try:
        # Download file from storage
        data = supabase.storage.from_('dhna-output-data').download(bucket_path)
        
        # Parse CSV
        df = pd.read_csv(io.BytesIO(data))
        return df
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load file: {str(e)}")

# ============================================================================
# ROOT ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    """API root - returns basic info"""
    return {
        "message": "DHNA Displacement Risk Assessment API (Reference-Based)",
        "version": "2.0.0",
        "architecture": "Storage bucket references",
        "docs": "/docs",
        "endpoints": {
            "files": "/api/files",
            "risk_summary": "/api/risk-summary",
            "risk_data": "/api/risk-data",
            "high_risk_areas": "/api/high-risk-areas",
            "population_data": "/api/population-data",
            "rent_data": "/api/rent-data",
            "stats": "/api/stats",
            "health": "/health"
        }
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        supabase.table('data_files').select("count", count="exact").execute()
        return {"status": "healthy", "database": "connected", "storage": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# ============================================================================
# FILE METADATA ENDPOINTS
# ============================================================================

@app.get("/api/files")
def list_files():
    """List all available data files"""
    try:
        response = supabase.table('data_files').select('*').order('uploaded_at', desc=True).execute()
        return {
            "count": len(response.data),
            "files": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/{file_type}")
def get_file_info(file_type: str):
    """Get metadata for a specific file type"""
    try:
        metadata = get_file_metadata(file_type)
        return metadata
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# RISK DATA ENDPOINTS
# ============================================================================

@app.get("/api/risk-summary")
def get_risk_summary():
    """Get summary of risk levels (from dashboard_stats for speed)"""
    try:
        # Try to get from cached stats first
        stats = supabase.table('dashboard_stats').select('*').eq('metric_name', 'risk_summary').execute()
        
        if stats.data:
            return stats.data[0]['metric_value']
        
        # Fallback: load from CSV
        metadata = get_file_metadata('risk_data')
        df = download_csv_from_storage(metadata['bucket_path'])
        
        risk_counts = df['risk_level'].value_counts().to_dict()
        return {
            "total_areas": len(df),
            "high_risk": risk_counts.get('high', 0),
            "medium_risk": risk_counts.get('medium', 0),
            "low_risk": risk_counts.get('low', 0)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/risk-data")
def get_risk_data(
    risk_level: Optional[str] = Query(None, description="Filter by risk level: high, medium, low"),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get displacement risk data"""
    try:
        # Get file metadata
        metadata = get_file_metadata('risk_data')
        
        # Download and parse CSV
        df = download_csv_from_storage(metadata['bucket_path'])
        
        # Filter by risk level if specified
        if risk_level:
            if risk_level not in ['high', 'medium', 'low']:
                raise HTTPException(status_code=400, detail="Invalid risk_level")
            df = df[df['risk_level'] == risk_level]
        
        # Apply limit
        df = df.head(limit)
        
        return {
            "count": len(df),
            "file_info": {
                "name": metadata['file_name'],
                "last_updated": metadata['last_updated']
            },
            "data": df.to_dict('records')
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/high-risk-areas")
def get_high_risk_areas():
    """Get all high-risk displacement areas"""
    try:
        metadata = get_file_metadata('risk_data')
        df = download_csv_from_storage(metadata['bucket_path'])
        
        high_risk = df[df['risk_level'] == 'high']
        
        return {
            "count": len(high_risk),
            "areas": high_risk.to_dict('records')
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/area/{gisjoin}")
def get_area_by_gisjoin(gisjoin: str):
    """Get detailed information for a specific area"""
    try:
        metadata = get_file_metadata('risk_data')
        df = download_csv_from_storage(metadata['bucket_path'])
        
        # Find area (try different column names)
        area = None
        for col in ['GISJOIN_proj', 'gisjoin_proj', 'GISJOIN', 'gisjoin']:
            if col in df.columns:
                area = df[df[col] == gisjoin]
                break
        
        if area is None or len(area) == 0:
            raise HTTPException(status_code=404, detail="Area not found")
        
        return area.to_dict('records')[0]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# POPULATION DATA ENDPOINTS
# ============================================================================

@app.get("/api/population-data")
def get_population_data(
    year: Optional[int] = Query(None, description="Filter by year"),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get population and demographic data"""
    try:
        metadata = get_file_metadata('population')
        df = download_csv_from_storage(metadata['bucket_path'])
        
        # Filter by year if specified
        if year and 'data_yr' in df.columns:
            df = df[df['data_yr'] == year]
        
        # Apply limit
        df = df.head(limit)
        
        return {
            "count": len(df),
            "file_info": {
                "name": metadata['file_name'],
                "last_updated": metadata['last_updated']
            },
            "data": df.to_dict('records')
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/population-trends")
def get_population_trends():
    """Get population trends over time"""
    try:
        metadata = get_file_metadata('population')
        df = download_csv_from_storage(metadata['bucket_path'])
        
        if 'data_yr' not in df.columns or 'pop' not in df.columns:
            raise HTTPException(status_code=400, detail="Required columns not found")
        
        trends = df.groupby('data_yr')['pop'].sum().reset_index()
        trends.columns = ['year', 'total_population']
        
        return {
            "trends": trends.to_dict('records')
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# RENT DATA ENDPOINTS
# ============================================================================

@app.get("/api/rent-data")
def get_rent_data(limit: int = Query(100, ge=1, le=1000)):
    """Get quarterly rent data"""
    try:
        metadata = get_file_metadata('rent')
        df = download_csv_from_storage(metadata['bucket_path'])
        
        # Apply limit
        df = df.head(limit)
        
        return {
            "count": len(df),
            "file_info": {
                "name": metadata['file_name'],
                "last_updated": metadata['last_updated']
            },
            "data": df.to_dict('records')
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# STATISTICS ENDPOINTS
# ============================================================================

@app.get("/api/stats")
def get_statistics():
    """Get overall statistics from cached dashboard stats"""
    try:
        # Get all dashboard stats
        response = supabase.table('dashboard_stats').select('*').execute()
        
        stats = {}
        for item in response.data:
            stats[item['metric_name']] = item['metric_value']
        
        # Add file info
        files = supabase.table('data_files').select('file_type, row_count, last_updated').execute()
        stats['files'] = files.data
        
        return stats
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# PIPELINE TRACKING ENDPOINTS
# ============================================================================

@app.get("/api/pipeline-runs")
def get_pipeline_runs(limit: int = Query(10, ge=1, le=50)):
    """Get recent pipeline runs"""
    try:
        response = supabase.table('pipeline_runs') \
            .select('*') \
            .order('run_date', desc=True) \
            .limit(limit) \
            .execute()
        
        return {
            "count": len(response.data),
            "runs": response.data
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# xd