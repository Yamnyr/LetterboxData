-- stg_tmdb
with raw_data as (
    select
        name as movie_title,
        year as release_year,
        tmdb_id,
        json_data
    from {{ source('raw', 'raw_tmdb_metadata') }}
)

select
    movie_title,
    release_year,
    tmdb_id,
    (json_data->>'$.title') as tmdb_title,
    (json_data->>'$.runtime')::INT as runtime_minutes,
    try_cast(nullif(json_data->>'$.release_date', '') as DATE) as tmdb_release_date,
    (json_data->>'$.vote_average')::DOUBLE as tmdb_vote_average,
    (json_data->>'$.vote_count')::INT as tmdb_vote_count,
    (json_data->>'$.popularity')::DOUBLE as tmdb_popularity,
    (json_data->>'$.original_language') as original_language,
    from_json(json_data->'$.origin_country', '["VARCHAR"]') as origin_countries,
    (json_data->>'$.overview') as overview,
    -- Extract genres as an array of names
    from_json(json_data->'$.genres', '["JSON"]') as genres_json,
    -- Extract production countries
    from_json(json_data->'$.production_countries', '["JSON"]') as countries_json,
    -- Extract spoken languages
    from_json(json_data->'$.spoken_languages', '["JSON"]') as languages_json,
    -- Extract cast
    from_json(json_data->'$.credits.cast', '["JSON"]') as cast_json,
    -- Extract crew
    from_json(json_data->'$.credits.crew', '["JSON"]') as crew_json
from raw_data
