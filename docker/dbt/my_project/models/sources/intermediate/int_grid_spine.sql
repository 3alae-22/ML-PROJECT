{{ config(materialized='table') }}

SELECT d.date, g.lat_grid, g.lon_grid
FROM (SELECT DISTINCT date FROM {{ ref('stg_fishing') }}) d
CROSS JOIN (
    SELECT DISTINCT lat AS lat_grid, lon AS lon_grid
    FROM {{ ref('stg_openmeteo_weather') }}
) g