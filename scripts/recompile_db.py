import os
import duckdb
import sys

# Ensure scripts directory is on path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.pipeline import compile_dbt_sql

DB_PATH = "letterboxd_data.duckdb"
dbt_project_dir = "dbt_project"

if not os.path.exists(DB_PATH):
    print(f"Error: {DB_PATH} not found.")
    sys.exit(1)

print(f"Connecting to DuckDB database: {DB_PATH}...")
db = duckdb.connect(DB_PATH)

# Recompile staging views
print("Recompiling staging models...")
staging_models = ['stg_tmdb', 'stg_watched', 'stg_ratings', 'stg_diary', 'stg_likes']
for model in staging_models:
    sql_path = os.path.join(dbt_project_dir, 'models', 'staging', f"{model}.sql")
    with open(sql_path, 'r', encoding='utf-8') as f:
        raw_sql = f.read()
    compiled_sql = compile_dbt_sql(raw_sql)
    db.execute(f"CREATE OR REPLACE VIEW {model} AS {compiled_sql}")
    print(f"  Compiled View: {model}")

# Recompile mart tables
print("Recompiling mart models...")
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
    print(f"  Compiled Table: {model}")

db.close()
print("Success! Database views and tables have been successfully updated.")
