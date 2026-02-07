-- mart_watchlist_recommendations
with watchlist as (
    select
        Name as movie_title,
        Year as release_year
    from {{ source('raw', 'raw_watchlist') }}
),

tmdb as (
    select
        movie_title,
        release_year,
        tmdb_vote_average,
        tmdb_vote_count,
        overview
    from {{ ref('stg_tmdb') }}
)

select
    w.*,
    t.tmdb_vote_average,
    t.tmdb_vote_count,
    t.overview
from watchlist w
join tmdb t on w.movie_title = t.movie_title and w.release_year = t.release_year
where t.tmdb_vote_average >= 7.5  -- Highly rated by community
order by t.tmdb_vote_average desc
