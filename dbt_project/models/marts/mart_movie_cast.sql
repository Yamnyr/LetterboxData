-- mart_movie_cast
with tmdb as (
    select
        movie_title,
        release_year,
        cast_json
    from {{ ref('stg_tmdb') }}
)

select
    movie_title,
    release_year,
    json_extract_string(member_json, '$.name') as name,
    json_extract_string(member_json, '$.character') as character,
    (json_extract_string(member_json, '$.order'))::INT as cast_order
from tmdb,
unnest(cast_json) as t(member_json)
where (json_extract_string(member_json, '$.order'))::INT < 10  -- Top 10 cast only
