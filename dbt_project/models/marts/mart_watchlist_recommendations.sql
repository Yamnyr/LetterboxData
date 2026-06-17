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
        overview,
        runtime_minutes,
        tmdb_popularity,
        tmdb_poster_path,
        tmdb_backdrop_path
    from {{ ref('stg_tmdb') }}
)

select
    w.*,
    t.tmdb_vote_average,
    t.tmdb_vote_count,
    t.overview,
    t.runtime_minutes,
    t.tmdb_popularity,
    t.tmdb_poster_path,
    t.tmdb_backdrop_path
from watchlist w
left join tmdb t on w.movie_title = t.movie_title and w.release_year = t.release_year
