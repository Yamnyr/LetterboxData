# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "PLEASE EDIT .env AND ADD YOUR TMDB_API_KEY BEFORE CONTINUING." -ForegroundColor Red
    exit
}

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt

# Step 1: Ingestion
Write-Host "Step 1: Ingesting data from Letterboxd CSVs and TMDB API..." -ForegroundColor Cyan
python scripts/ingest_tmdb.py

# Step 2: dbt Transformations
Write-Host "Step 2: Running dbt transformations..." -ForegroundColor Cyan
cd dbt_project
dbt run --profiles-dir .
cd ..

# Step 3: Launch Dashboard
Write-Host "Step 3: Launching Streamlit dashboard..." -ForegroundColor Cyan
streamlit run app.py
