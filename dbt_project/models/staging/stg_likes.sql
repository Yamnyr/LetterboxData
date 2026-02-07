-- stg_likes
select
    strptime(Date, '%Y-%m-%d')::DATE as like_date,
    Name as movie_title,
    Year::INT as release_year,
    "Letterboxd URI" as letterboxd_uri
from {{ source('raw', 'raw_likes') }}
