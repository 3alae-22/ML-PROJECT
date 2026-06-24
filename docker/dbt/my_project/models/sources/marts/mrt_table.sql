{{ config(materialized='table') }}

select
    date,
    lat_grid,
    lon_grid,

    fishing_hours,
    (fishing_hours > 0)::int as is_fishing,
    geartype,

    extract(month from date) as month,
    extract(dow from date) as day_of_week,
    extract(quarter from date) as quarter,

    sst,
    salinity,
    current_u,
    current_v,

    wave_height_max,
    wave_period_max,
    swell_height_max,
    wind_speed_max,
    wind_dir

from {{ ref('int_features') }}
order by date, lat_grid, lon_grid
