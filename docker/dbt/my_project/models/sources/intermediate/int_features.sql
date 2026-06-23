{{ config(materialized='table') }}

SELECT
    spine.date,
    spine.lat_grid,
    spine.lon_grid,

    COALESCE(f.hours, 0) AS fishing_hours,
    COALESCE(f.vessel_ids, 0) AS vessel_ids,
    COALESCE(f.geartype, 'no_fishing') AS geartype,

    c.sst,
    c.salinity,
    c.current_u,
    c.current_v,

    w.wave_height_max,
    w.wave_period_max,
    w.swell_height_max,
    w.wind_speed_max,
    w.wind_dir

FROM {{ ref('int_grid_spine') }} spine
LEFT JOIN {{ ref('stg_fishing') }} f
    ON spine.date = f.date
    AND spine.lat_grid = f.lat_grid
    AND spine.lon_grid = f.lon_grid
LEFT JOIN {{ ref('stg_copernicus') }} c
    ON spine.date = c.date
    AND spine.lat_grid = c.lat_grid
    AND spine.lon_grid = c.lon_grid
LEFT JOIN {{ ref('stg_openmeteo_weather') }} w
    ON spine.date = w.date
    AND spine.lat_grid = w.lat
    AND spine.lon_grid = w.lon