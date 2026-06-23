{{ config(materialized='table') }}

SELECT
    date,
    lat_grid,
    lon_grid,

    fishing_hours,
    (fishing_hours > 0)::int AS is_fishing,
    geartype,

    EXTRACT(MONTH FROM date) AS month,
    EXTRACT(DOW FROM date) AS day_of_week,
    EXTRACT(QUARTER FROM date) AS quarter,

    sst,
    salinity,
    current_u,
    current_v,

    wave_height_max,
    wave_period_max,
    swell_height_max,
    wind_speed_max,
    wind_dir

FROM {{ ref('int_features') }}
ORDER BY lat_grid, lon_grid, date