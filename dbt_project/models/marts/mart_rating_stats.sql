-- mart_rating_stats
with global_avg as (
    select avg(rating_value) as avg_rating
    from {{ ref('stg_ratings') }}
)

select
    r.movie_title,
    r.release_year,
    r.rating_value,
    g.avg_rating,
    (r.rating_value - g.avg_rating) as rating_diff,
    case 
        when r.rating_value > g.avg_rating then 'Higher than average'
        when r.rating_value < g.avg_rating then 'Lower than average'
        else 'Average'
    end as comparison
from {{ ref('stg_ratings') }} r, global_avg g
