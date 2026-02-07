-- mart_movie_countries
with tmdb as (
    select
        movie_title,
        release_year,
        countries_json
    from {{ ref('stg_tmdb') }}
)

select
    movie_title,
    release_year,
    json_extract_string(country_json, '$.name') as country_name,
    json_extract_string(country_json, '$.iso_3166_1') as country_code
from tmdb,
unnest(countries_json) as t(country_json)
