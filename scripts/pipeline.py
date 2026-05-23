import os
import zipfile
import re
import shutil
import json
import time
import requests
import pandas as pd
import duckdb

def unzip_and_locate_csvs(zip_file, extract_to):
    """
    Extracts the Letterboxd ZIP archive and finds the directory containing CSV files.
    """
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    
    # Walk through the extracted files to find 'watched.csv'
    for root, dirs, files in os.walk(extract_to):
        if 'watched.csv' in files:
            return root
            
    raise ValueError("Could not find 'watched.csv' in the uploaded ZIP file. Ensure it is a valid Letterboxd export ZIP.")

def compile_dbt_sql(sql_content):
    """
    Compiles DBT SQL syntax into standard DuckDB SQL syntax by replacing ref() and source().
    """
    # Replace source('raw', 'raw_xxx') or source("raw", "raw_xxx")
    sql = re.sub(
        r"\{\{\s*source\(['\"]\w+['\"]\s*,\s*['\"](\w+)['\"]\)\s*\}\}", 
        r"\1", 
        sql_content
    )
    # Replace ref('table_name') or ref("table_name")
    sql = re.sub(
        r"\{\{\s*ref\(['\"](\w+)['\"]\)\s*\}\}", 
        r"\1", 
        sql
    )
    return sql

def fetch_tmdb_data(name, year, tmdb_api_key):
    """
    Fetches details for a single movie from the TMDB API.
    """
    if not tmdb_api_key or tmdb_api_key == "your_api_key_here":
        return None

    search_url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": tmdb_api_key,
        "query": name
    }
    if year:
        try:
            params["primary_release_year"] = int(float(year))
        except:
            pass
    
    try:
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        results = response.json().get('results', [])
        
        # Fallback if no results with year, search without it
        if not results and year:
            params.pop("primary_release_year", None)
            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            results = response.json().get('results', [])

        if not results:
            return None
            
        movie_id = results[0]['id']
        
        # Get details + credits
        details_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        detail_params = {
            "api_key": tmdb_api_key,
            "append_to_response": "credits"
        }
        
        detail_response = requests.get(details_url, params=detail_params, timeout=10)
        detail_response.raise_for_status()
        return detail_response.json()
        
    except Exception as e:
        print(f"Error fetching {name} ({year}): {e}")
        return None

def run_dynamic_pipeline(csv_dir, db_path, dbt_project_dir, tmdb_api_key, progress_callback=None):
    """
    Ingests CSVs, fetches missing TMDB metadata (with progress callback),
    and executes all DBT transformation models.
    """
    db = duckdb.connect(db_path)
    
    # 1. Ensure raw_tmdb_metadata table exists
    db.execute("""
        CREATE TABLE IF NOT EXISTS raw_tmdb_metadata (
            name VARCHAR,
            year INTEGER,
            tmdb_id INTEGER,
            json_data JSON,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 2. Define expected raw schemas in case any files are missing in user ZIP
    schemas = {
        "raw_watched": '(Date VARCHAR, Name VARCHAR, Year INTEGER, "Letterboxd URI" VARCHAR)',
        "raw_ratings": '(Date VARCHAR, Name VARCHAR, Year INTEGER, Rating DOUBLE, "Letterboxd URI" VARCHAR)',
        "raw_diary": '(Date VARCHAR, Name VARCHAR, Year INTEGER, Rating DOUBLE, Rewatch VARCHAR, Tags VARCHAR, "Watched Date" VARCHAR, Review VARCHAR, Spoiler VARCHAR, "Letterboxd URI" VARCHAR)',
        "raw_watchlist": '(Date VARCHAR, Name VARCHAR, Year INTEGER, "Letterboxd URI" VARCHAR)',
        "raw_likes": '(Date VARCHAR, Name VARCHAR, Year INTEGER, "Letterboxd URI" VARCHAR)'
    }
    
    # 3. Load uploaded CSV files into raw tables
    csv_mappings = {
        "raw_watched": "watched.csv",
        "raw_ratings": "ratings.csv",
        "raw_diary": "diary.csv",
        "raw_watchlist": "watchlist.csv",
        "raw_likes": os.path.join("likes", "films.csv")
    }
    
    for table_name, csv_rel_path in csv_mappings.items():
        csv_path = os.path.join(csv_dir, csv_rel_path)
        if os.path.exists(csv_path):
            print(f"Loading {csv_path} into {table_name}...")
            try:
                # Use pandas to load CSV safely
                df = pd.read_csv(csv_path)
                db.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df")
            except Exception as e:
                print(f"Failed to load CSV {csv_path}: {e}. Creating empty table.")
                db.execute(f"CREATE OR REPLACE TABLE {table_name} {schemas[table_name]}")
        else:
            print(f"File {csv_path} not found. Initializing empty table {table_name}.")
            db.execute(f"CREATE OR REPLACE TABLE {table_name} {schemas[table_name]}")
            
    # 4. Find unique films and identify which ones are missing in raw_tmdb_metadata
    # This query matches what ingest_tmdb.py does to get unique films
    films_dfs = []
    for t in ['raw_watched', 'raw_ratings', 'raw_watchlist']:
        try:
            df = db.execute(f"SELECT Name, Year FROM {t}").df()
            if not df.empty:
                films_dfs.append(df[['Name', 'Year']])
        except:
            pass
            
    if films_dfs:
        all_films = pd.concat(films_dfs).drop_duplicates().reset_index(drop=True)
        # Normalize column types
        all_films['Year'] = pd.to_numeric(all_films['Year'], errors='coerce')
        all_films = all_films.dropna(subset=['Name'])
    else:
        all_films = pd.DataFrame(columns=['Name', 'Year'])
        
    # Get already fetched films from cache
    fetched_films = db.execute("SELECT name, year FROM raw_tmdb_metadata").df()
    
    if not fetched_films.empty and not all_films.empty:
        fetched_films.columns = ['Name', 'Year']
        fetched_films['Year'] = pd.to_numeric(fetched_films['Year'], errors='coerce')
        
        # Merge to find films that haven't been fetched
        missing_films = pd.merge(all_films, fetched_films, on=['Name', 'Year'], how='left', indicator=True)
        missing_films = missing_films[missing_films['_merge'] == 'left_only'][['Name', 'Year']]
    else:
        missing_films = all_films
        
    missing_films = missing_films.drop_duplicates().reset_index(drop=True)
    
    # 5. Ingest missing movies from TMDB (with progress reporting & parallel multi-threading)
    total_missing = len(missing_films)
    if total_missing > 0 and tmdb_api_key and tmdb_api_key != "your_api_key_here":
        print(f"Need to fetch {total_missing} films from TMDB API.")
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def fetch_single(row):
            name = row['Name']
            year = row['Year']
            try:
                year_val = int(float(year)) if pd.notnull(year) else None
            except:
                year_val = None
            data = fetch_tmdb_data(name, year_val, tmdb_api_key)
            return name, year_val, data

        max_workers = min(15, total_missing)
        fetched_count = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_row = {
                executor.submit(fetch_single, row): row 
                for _, row in missing_films.iterrows()
            }
            
            for future in as_completed(future_to_row):
                name, year_val, data = future.result()
                fetched_count += 1
                
                if progress_callback:
                    progress_callback(
                        fetched_count, 
                        total_missing, 
                        f"Enrichi : {name} ({year_val if year_val else 'N/A'})"
                    )
                
                if data:
                    json_str = json.dumps(data)
                    db.execute(
                        "INSERT INTO raw_tmdb_metadata (name, year, tmdb_id, json_data) VALUES (?, ?, ?, ?)",
                        [name, year_val, data.get('id'), json_str]
                    )
    elif total_missing > 0:
        print("Missing films found but no TMDB API key available. Skipping metadata fetching.")
        if progress_callback:
            progress_callback(0, 0, "Attention : Clé TMDB API non configurée. Certains nouveaux films n'auront pas de métadonnées.")
            
    # 6. Compile and execute staging models (Views)
    staging_models = ['stg_tmdb', 'stg_watched', 'stg_ratings', 'stg_diary', 'stg_likes']
    for model in staging_models:
        sql_path = os.path.join(dbt_project_dir, 'models', 'staging', f"{model}.sql")
        with open(sql_path, 'r', encoding='utf-8') as f:
            raw_sql = f.read()
        compiled_sql = compile_dbt_sql(raw_sql)
        db.execute(f"CREATE OR REPLACE VIEW {model} AS {compiled_sql}")
        
    # 7. Compile and execute mart models (Tables)
    mart_models = [
        'mart_movies',
        'mart_movie_genres',
        'mart_movie_countries',
        'mart_movie_origin_countries',
        'mart_movie_crew',
        'mart_movie_cast',
        'mart_rating_stats',
        'mart_watchlist_recommendations'
    ]
    for model in mart_models:
        sql_path = os.path.join(dbt_project_dir, 'models', 'marts', f"{model}.sql")
        with open(sql_path, 'r', encoding='utf-8') as f:
            raw_sql = f.read()
        compiled_sql = compile_dbt_sql(raw_sql)
        db.execute(f"CREATE OR REPLACE TABLE {model} AS {compiled_sql}")
        
    db.close()
    print("Pipeline compilation and execution complete.")

def load_all_dataframes_from_db(db_path):
    """
    Loads all staged and mart tables into pandas dataframes from a given database connection.
    """
    con = duckdb.connect(db_path, read_only=True)
    tables = [
        "mart_movies", "stg_watched", "stg_ratings", "mart_movie_genres",
        "mart_movie_countries", "mart_movie_crew", "mart_movie_cast",
        "stg_diary", "stg_likes", "mart_rating_stats", "mart_watchlist_recommendations"
    ]
    dfs = {}
    for table in tables:
        try:
            dfs[table] = con.execute(f"SELECT * FROM {table}").df()
        except Exception as e:
            dfs[table] = pd.DataFrame()
    con.close()
    return dfs
