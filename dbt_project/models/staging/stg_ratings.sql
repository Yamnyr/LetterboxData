-- stg_ratings
select
    strptime(Date, '%Y-%m-%d')::DATE as rating_date,
    Name as movie_title,
    Year::INT as release_year,
    Rating::DOUBLE as rating_value,
    "Letterboxd URI" as letterboxd_uri
from {{ source('raw', 'raw_ratings') }}
