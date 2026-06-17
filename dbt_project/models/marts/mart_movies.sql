-- mart_movies
with movies as (
    select
        movie_title,
        release_year,
        tmdb_id,
        tmdb_title,
        runtime_minutes,
        tmdb_release_date,
        tmdb_vote_average,
        tmdb_vote_count,
        tmdb_popularity,
        original_language,
        origin_countries,
        overview,
        tmdb_poster_path,
        tmdb_backdrop_path
    from {{ ref('stg_tmdb') }}
),

ratings as (
    select
        movie_title,
        release_year,
        avg(rating_value) as user_avg_rating,
        max(rating_value) as user_max_rating
    from {{ ref('stg_ratings') }}
    group by 1, 2
)

select
    m.*,
    r.user_avg_rating,
    r.user_max_rating
from movies m
left join ratings r on m.movie_title = r.movie_title and m.release_year = r.release_year
