from airflow.sdk import dag, task
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner' : 'airflow',
    'retries' : 2,
    'retry_delay': timedelta(minutes=5),
}

@dag(
    dag_id='data_pipeline',
    schedule='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=['fishing', 'data'],
)
def data_pipeline():

    @task
    def extract_gfw():
        import psycopg2
        import time
        import sys
        sys.path.append('/opt/airflow/dags')
        from src.ingestion.gfw_request import fetch_gfw

        YEARS = [
            ("2021-10-01", "2021-12-31"),
            ("2022-01-01", "2022-12-31"),
            ("2023-01-01", "2023-12-31"),
            ("2024-01-01", "2024-12-31"),
            ("2025-01-01", "2025-12-31"),
        ]

        conn = psycopg2.connect(
            host="postgres_container", port=5432,
            dbname="db", user="db_user", password="db_password"
        )

        try:
            with conn.cursor() as cursor:
                cursor.execute("CREATE SCHEMA IF NOT EXISTS dev;")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS dev.raw_fishing(
                        date DATE, lat FLOAT, lon FLOAT,
                        lat_grid FLOAT, lon_grid FLOAT,
                        hours FLOAT, geartype VARCHAR(50), vessel_ids INT,
                        PRIMARY KEY (date, lat, lon, geartype)
                    );
                """)
            conn.commit()

            for date_start, date_end in YEARS:
                data    = fetch_gfw(date_start, date_end)
                records = data["entries"][0]["public-global-fishing-effort:v4.0"]

                def snap(value, resolution=0.25):
                    return round(round(value / resolution) * resolution, 2)

                rows = [(
                    e["date"], e["lat"], e["lon"],
                    snap(e["lat"]), snap(e["lon"]),
                    e["hours"], e["geartype"], e["vesselIDs"],
                ) for e in records]

                with conn.cursor() as cursor:
                    cursor.executemany("""
                        INSERT INTO dev.raw_fishing(
                            date, lat, lon, lat_grid, lon_grid,
                            hours, geartype, vessel_ids
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (date, lat, lon, geartype) DO NOTHING;
                    """, rows)
                conn.commit()
                print(f"GFW {date_start} → {len(rows)} rows")
                time.sleep(3)
        finally:
            conn.close()

    @task
    def extract_copernicus():
        import psycopg2
        import time
        import sys
        sys.path.append('/opt/airflow/dags')
        from src.ingestion.copernicus_request import fetch_copernicus

        YEARS = [
            ("2021-10-01", "2021-12-31"),
            ("2022-01-01", "2022-12-31"),
            ("2023-01-01", "2023-12-31"),
            ("2024-01-01", "2024-12-31"),
            ("2025-01-01", "2025-12-31"),
        ]

        def snap(value, resolution=0.25):
            return round(round(value / resolution) * resolution, 2)

        conn = psycopg2.connect(
            host="postgres_container", port=5432,
            dbname="db", user="db_user", password="db_password"
        )

        try:
            with conn.cursor() as cursor:
                cursor.execute("CREATE SCHEMA IF NOT EXISTS dev;")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS dev.raw_copernicus(
                        date DATE, lat FLOAT, lon FLOAT,
                        lat_grid FLOAT, lon_grid FLOAT,
                        sst FLOAT, salinity FLOAT,
                        current_u FLOAT, current_v FLOAT,
                        PRIMARY KEY (date, lat, lon)
                    );
                """)
            conn.commit()

            for date_start, date_end in YEARS:
                ds        = fetch_copernicus(date_start, date_end)
                ds_loaded = ds.isel(depth=0).load()
                rows      = []

                for t in ds_loaded.time.values:
                    date = str(t)[:10]
                    ds_t = ds_loaded.sel(time=t)
                    for lat in ds_loaded.latitude.values:
                        for lon in ds_loaded.longitude.values:
                            point = ds_t.sel(latitude=lat, longitude=lon)
                            rows.append((
                                date,
                                round(float(lat), 4),
                                round(float(lon), 4),
                                snap(float(lat)), snap(float(lon)),
                                float(point["thetao"].values),
                                float(point["so"].values),
                                float(point["uo"].values),
                                float(point["vo"].values),
                            ))

                with conn.cursor() as cursor:
                    cursor.executemany("""
                        INSERT INTO dev.raw_copernicus(
                            date, lat, lon, lat_grid, lon_grid,
                            sst, salinity, current_u, current_v
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (date, lat, lon) DO NOTHING;
                    """, rows)
                conn.commit()
                print(f"Copernicus {date_start} → {len(rows)} rows")
                time.sleep(3)
        finally:
            conn.close()

    @task
    def extract_marine_weather():
        import psycopg2
        import numpy as np
        import time
        import sys
        sys.path.append('/opt/airflow/dags')
        from src.ingestion.open_meteo_request import fetch_marine, fetch_wind, is_ocean_point

        YEARS = [
            ("2021-10-01", "2021-12-31"),
            ("2022-01-01", "2022-12-31"),
            ("2023-01-01", "2023-12-31"),
            ("2024-01-01", "2024-12-31"),
            ("2025-01-01", "2025-12-31"),
        ]

        lats = [round(float(x), 2) for x in np.arange(29.25, 36.25, 0.25)]
        lons = [round(float(x), 2) for x in np.arange(-15.0, -9.25, 0.25)]
        grid = [(lat, lon) for lat in lats for lon in lons]

        conn = psycopg2.connect(
            host="postgres_container", port=5432,
            dbname="db", user="db_user", password="db_password"
        )

        try:
            with conn.cursor() as cursor:
                cursor.execute("CREATE SCHEMA IF NOT EXISTS dev;")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS dev.raw_marine_weather(
                        date DATE, lat FLOAT, lon FLOAT,
                        wave_height_max FLOAT, wave_period_max FLOAT,
                        swell_height_max FLOAT, wind_speed_max FLOAT,
                        wind_dir FLOAT,
                        PRIMARY KEY (date, lat, lon)
                    );
                """)
            conn.commit()

            for lat, lon in grid:
                check = fetch_marine(lat, lon, "2023-01-01", "2023-01-07")
                if check is None or not is_ocean_point(check):
                    print(f"SKIP {lat},{lon} — land")
                    continue

                for date_start, date_end in YEARS:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            SELECT COUNT(*) FROM dev.raw_marine_weather
                            WHERE lat=%s AND lon=%s
                            AND date BETWEEN %s AND %s
                        """, (lat, lon, date_start, date_end))
                        if cursor.fetchone()[0] > 0:
                            continue

                    data_marine = fetch_marine(lat, lon, date_start, date_end)
                    time.sleep(0.5)
                    data_wind   = fetch_wind(lat, lon, date_start, date_end)
                    time.sleep(0.5)

                    if data_marine is None or data_wind is None:
                        print(f"FAIL {lat},{lon} {date_start}")
                        continue

                    marine = data_marine["daily"]
                    wind   = data_wind["daily"]
                    rows   = [(
                        marine["time"][i],
                        float(lat), float(lon),
                        marine["wave_height_max"][i],
                        marine["wave_period_max"][i],
                        marine["swell_wave_height_max"][i],
                        wind["wind_speed_10m_max"][i],
                        wind["wind_direction_10m_dominant"][i],
                    ) for i in range(len(marine["time"]))]

                    with conn.cursor() as cursor:
                        cursor.executemany("""
                            INSERT INTO dev.raw_marine_weather(
                                date, lat, lon, wave_height_max,
                                wave_period_max, swell_height_max,
                                wind_speed_max, wind_dir
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                            ON CONFLICT (date, lat, lon) DO NOTHING;
                        """, rows)
                    conn.commit()
                    print(f"OK {lat},{lon} {date_start} → {len(rows)} rows")
        finally:
            conn.close()

    # dbt run via BashOperator
    dbt_run = BashOperator(
        task_id='dbt_run',
        bash_command='docker exec dbt_container dbt run --project-dir /usr/app',
    )

    @task
    def build_features():
        import sys
        sys.path.append('/opt/airflow/dags')
        from build_features import build_features as _build
        _build()

    # pipeline order
    gfw = extract_gfw()
    cop = extract_copernicus()
    marine = extract_marine_weather()
    feats = build_features()

    # extract in parallel -> dbt -> features
    [gfw, cop, marine] >> dbt_run >> feats


data_pipeline()