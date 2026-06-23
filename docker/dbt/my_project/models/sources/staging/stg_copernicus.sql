{{ config(
    materialized='incremental',
    unique_key=['date', 'lat_grid', 'lon_grid']
) }}

WITH source AS (
    SELECT *
    FROM {{ source('dev', 'raw_copernicus') }}
),

de_dup AS (
    SELECT DISTINCT ON (date, lat_grid, lon_grid) *
    FROM source
    ORDER BY date, lat_grid, lon_grid
)

SELECT
    date,
    lat_grid,
    lon_grid,
    NULLIF(sst, 'NaN'::float) AS sst,
    NULLIF(salinity, 'NaN'::float) AS salinity,
    NULLIF(current_u, 'NaN'::float) AS current_u,
    NULLIF(current_v, 'NaN'::float) AS current_v
FROM de_dup