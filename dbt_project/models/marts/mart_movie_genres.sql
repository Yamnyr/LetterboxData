-- mart_movie_genres
with tmdb as (
    select
        movie_title,
        release_year,
        genres_json
    from {{ ref('stg_tmdb') }}
)

select
    movie_title,
    release_year,
    json_extract_string(genre_json, '$.name') as genre_name
from tmdb,
unnest(genres_json) as t(genre_json)
