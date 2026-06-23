from open_meteo_request import fetch_marine, fetch_wind, is_ocean_point, GRID_POINTS
import psycopg2
import numpy as np
import time

YEARS = [
    ("2021-10-01", "2021-12-31"),
    ("2022-01-01", "2022-12-31"),
    ("2023-01-01", "2023-12-31"),
    ("2024-01-01", "2024-12-31"),
    ("2025-01-01", "2025-12-31"),
]

def connect_to_db():
    print("Connecting to PostgreSQL database...")
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5000,
            dbname="db",
            user="db_user",
            password="db_password"
        )
        return conn
    except psycopg2.Error as e:
        print(f"Database connection failed: {e}")
        raise

def create_table(conn):
    print("Creating table if not exists...")
    try:
        with conn.cursor() as cursor:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS dev;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dev.raw_marine_weather(
                    date DATE,
                    lat  FLOAT,
                    lon  FLOAT,
                    wave_height_max FLOAT,
                    wave_period_max FLOAT,
                    swell_height_max FLOAT,
                    wind_speed_max FLOAT,
                    wind_dir FLOAT,
                    PRIMARY KEY (date, lat, lon)
                );
            """)
        conn.commit()
        print("Table created.")
    except psycopg2.Error as e:
        print(f"Failed to create table: {e}")
        raise

def already_ingested(conn, lat, lon, date_start, date_end):
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) FROM dev.raw_marine_weather
            WHERE lat = %s AND lon = %s
            AND date BETWEEN %s AND %s
        """, (lat, lon, date_start, date_end))
        return cursor.fetchone()[0] > 0

def insert_records(conn, lat, lon, data_marine, data_wind):
    try:
        with conn.cursor() as cursor:
            marine = data_marine["daily"]
            wind = data_wind["daily"]
            rows = [
                (
                    marine["time"][i],
                    float(lat),
                    float(lon),
                    marine["wave_height_max"][i],
                    marine["wave_period_max"][i],
                    marine["swell_wave_height_max"][i],
                    wind["wind_speed_10m_max"][i],
                    wind["wind_direction_10m_dominant"][i],
                )
                for i in range(len(marine["time"]))
            ]
            cursor.executemany("""
                INSERT INTO dev.raw_marine_weather(
                    date, lat, lon,
                    wave_height_max, wave_period_max, swell_height_max,
                    wind_speed_max, wind_dir
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date, lat, lon) DO NOTHING;
            """, rows)
        conn.commit()
        return len(rows)
    except psycopg2.Error as e:
        print(f"Error inserting data: {e}")
        raise

if __name__ == "__main__":
    valid   = 0
    skipped = 0
    failed  = 0

    lats = [round(float(x), 2) for x in np.arange(29.25, 36.25, 0.25)]
    lons = [round(float(x), 2) for x in np.arange(-15.0, -9.25, 0.25)]
    GRID_POINTS = [(lat, lon) for lat in lats for lon in lons]

    conn = connect_to_db()
    create_table(conn)

    try:
        for lat, lon in GRID_POINTS:

            check = fetch_marine(lat, lon, "2023-01-01", "2023-01-07")
            if check is None or not is_ocean_point(check):
                print(f"SKIP lat={lat}, lon={lon} terre ferme")
                skipped += 1
                continue

            point_failed = False

            for date_start, date_end in YEARS:
                if already_ingested(conn, lat, lon, date_start, date_end):
                    print(f"SKIP lat={lat} lon={lon} {date_start[:4]} already ingested")
                    continue

                data_marine = fetch_marine(lat, lon, date_start, date_end)
                time.sleep(0.5)
                data_wind   = fetch_wind(lat, lon, date_start, date_end)
                time.sleep(0.5)

                if data_marine is None or data_wind is None:
                    print(f"  FAIL {date_start} -> {date_end}")
                    point_failed = True
                    continue

                n = insert_records(conn, lat, lon, data_marine, data_wind)
                print(f"  OK lat={lat} lon={lon} {date_start[:4]} -> {n} rows")

            if point_failed:
                failed += 1
            else:
                valid += 1

    finally:
        conn.close()

    print(f"\nValides  : {valid}")
    print(f"Skipped  : {skipped}")
    print(f"Echecs   : {failed}")