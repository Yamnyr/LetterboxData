import os
import pandas as pd
import requests
import duckdb
from dotenv import load_dotenv
import time
import json

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
DATA_DIR = os.getenv("LETTERBOXD_DATA_DIR", "data")
DB_PATH = os.getenv("DUCKDB_PATH", "letterboxd_data.duckdb")

def get_unique_films():
    watched_path = os.path.join(DATA_DIR, "watched.csv")
    ratings_path = os.path.join(DATA_DIR, "ratings.csv")
    watchlist_path = os.path.join(DATA_DIR, "watchlist.csv")
    
    films = []
    if os.path.exists(watched_path):
        df_w = pd.read_csv(watched_path)
        films.append(df_w[['Name', 'Year']])
    
    if os.path.exists(ratings_path):
        df_r = pd.read_csv(ratings_path)
        films.append(df_r[['Name', 'Year']])

    if os.path.exists(watchlist_path):
        df_wl = pd.read_csv(watchlist_path)
        films.append(df_wl[['Name', 'Year']])
        
    if not films:
        return pd.DataFrame(columns=['Name', 'Year'])
        
    all_films = pd.concat(films).drop_duplicates().reset_index(drop=True)
    return all_films

def fetch_tmdb_data(name, year):
    if not TMDB_API_KEY or TMDB_API_KEY == "your_api_key_here":
        print("Error: TMDB_API_KEY not set in .env")
        return None

    # Search for movie
    search_url = f"https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": name
    }
    if year:
        params["primary_release_year"] = year
    
    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        results = response.json().get('results', [])
        
        # If no results and we used a year, try searching without the year as a fallback
        if not results and year:
            print(f"No results with year {year} for {name}, trying without year...")
            params.pop("primary_release_year")
            response = requests.get(search_url, params=params)
            response.raise_for_status()
            results = response.json().get('results', [])

        if not results:
            print(f"No results found for {name}")
            return None
            
        movie_id = results[0]['id']
        
        # Get details + credits
        details_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        detail_params = {
            "api_key": TMDB_API_KEY,
            "append_to_response": "credits"
        }
        
        detail_response = requests.get(details_url, params=detail_params)
        detail_response.raise_for_status()
        return detail_response.json()
        
    except Exception as e:
        print(f"Error fetching {name} ({year}): {e}")
        return None

def main():
    if not os.path.exists(DATA_DIR):
        print(f"Error: Data directory {DATA_DIR} not found.")
        return

    db = duckdb.connect(DB_PATH)
    
    # Create table for raw metadata if it doesn't exist
    db.execute("""
        CREATE TABLE IF NOT EXISTS raw_tmdb_metadata (
            name VARCHAR,
            year INTEGER,
            tmdb_id INTEGER,
            json_data JSON,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Also load the CSVs as raw tables for dbt to use as sources
    csv_files = ["watched.csv", "ratings.csv", "diary.csv", "watchlist.csv"]
    for csv_file in csv_files:
        path = os.path.join(DATA_DIR, csv_file)
        if os.path.exists(path):
            table_name = f"raw_{csv_file.split('.')[0]}"
            print(f"Loading {csv_file} into {table_name}...")
            df = pd.read_csv(path)
            db.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df")

    # Load Likes
    likes_path = os.path.join(DATA_DIR, "likes", "films.csv")
    if os.path.exists(likes_path):
        print("Loading likes/films.csv into raw_likes...")
        df_likes = pd.read_csv(likes_path)
        db.execute("CREATE OR REPLACE TABLE raw_likes AS SELECT * FROM df_likes")
    else:
        # Create empty table if file doesn't exist to avoid dbt errors
        db.execute("CREATE OR REPLACE TABLE raw_likes (Date DATE, Name VARCHAR, Year INTEGER, [Letterboxd URI] VARCHAR)")

    all_films = get_unique_films()
    print(f"Found {len(all_films)} unique films.")
    
    # Get already fetched films
    fetched_films = db.execute("SELECT name, year FROM raw_tmdb_metadata").df()
    
    # Merge to find missing ones
    if not fetched_films.empty:
        # Normalize column names to avoid case issues (DuckDB often returns lowercase)
        fetched_films.columns = ['Name', 'Year']
        missing_films = pd.merge(all_films, fetched_films, on=['Name', 'Year'], how='left', indicator=True)
        missing_films = missing_films[missing_films['_merge'] == 'left_only'][['Name', 'Year']]
    else:
        missing_films = all_films
        
    print(f"Need to fetch {len(missing_films)} films.")
    
    for i, row in missing_films.iterrows():
        name = row['Name']
        # Handle NaN/Float years from Letterboxd CSV
        try:
            year = int(float(row['Year'])) if pd.notnull(row['Year']) else None
        except:
            year = None
            
        print(f"Fetching {name} ({year if year else 'N/A'})...")
        data = fetch_tmdb_data(name, year)
        
        if data:
            json_str = json.dumps(data)
            db.execute("INSERT INTO raw_tmdb_metadata (name, year, tmdb_id, json_data) VALUES (?, ?, ?, ?)",
                       [name, year, data.get('id'), json_str])
        else:
            # Optionally insert a null record to avoid re-fetching failed searches
            # db.execute("INSERT INTO raw_tmdb_metadata (name, year, tmdb_id, json_data) VALUES (?, ?, ?, ?)",
            #            [name, year, None, None])
            pass
        
        # Rate limiting (TMDB allows 40 requests per 10 seconds, but let's be safe)
        time.sleep(0.2)
        
    print("Ingestion complete.")
    db.close()

if __name__ == "__main__":
    main()
