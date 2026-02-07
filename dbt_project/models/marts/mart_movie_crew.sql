-- mart_movie_crew
with tmdb as (
    select
        movie_title,
        release_year,
        crew_json
    from {{ ref('stg_tmdb') }}
)

select
    movie_title,
    release_year,
    json_extract_string(member_json, '$.name') as name,
    json_extract_string(member_json, '$.job') as job,
    json_extract_string(member_json, '$.department') as department
from tmdb,
unnest(crew_json) as t(member_json)
where json_extract_string(member_json, '$.job') = 'Director'
