-- mart_movie_origin_countries
with tmdb as (
    select
        movie_title,
        release_year,
        origin_countries
    from {{ ref('stg_tmdb') }}
)

select
    movie_title,
    release_year,
    country_code
from tmdb,
unnest(origin_countries) as t(country_code)
