{{ config(
    materialized='incremental',
    unique_key=['date', 'lat', 'lon']
)}}

WITH source AS (
    SELECT *
    FROM {{ source('dev', 'raw_marine_weather') }}
),

de_dup AS (
    SELECT DISTINCT ON (date, lat, lon) *
    FROM source
    ORDER BY date, lat, lon
)

SELECT
    date,
    lat,
    lon,
    NULLIF(wave_height_max, 'NaN'::float) AS wave_height_max,
    NULLIF(wave_period_max, 'NaN'::float) AS wave_period_max,
    NULLIF(swell_height_max, 'NaN'::float) AS swell_height_max,
    NULLIF(wind_speed_max, 'NaN'::float) AS wind_speed_max,
    NULLIF(wind_dir, 'NaN'::float) AS wind_dir
FROM de_dup