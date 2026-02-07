-- stg_diary
select
    strptime(Date, '%Y-%m-%d')::DATE as diary_date,
    Name as movie_title,
    Year::INT as release_year,
    Rating as rating_value,
    Rewatch = 'Yes' as is_rewatch
from {{ source('raw', 'raw_diary') }}
