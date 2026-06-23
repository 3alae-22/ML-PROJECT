{{ config(
    materialized='incremental',
    unique_key=['date', 'lat_grid', 'lon_grid']
) }}

WITH source AS (
    SELECT *
    FROM {{ source('dev', 'raw_fishing') }}
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
    NULLIF(hours, 'NaN'::float) AS hours,
    NULLIF(geartype, '') AS geartype,
    vessel_ids AS vessel_ids
FROM de_dup