import psycopg2
import time
from copernicus_request import fetch_copernicus

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
                CREATE TABLE IF NOT EXISTS dev.raw_copernicus(
                    date DATE,
                    lat FLOAT,
                    lon FLOAT,
                    lat_grid FLOAT,
                    lon_grid FLOAT,
                    sst FLOAT,
                    salinity FLOAT,
                    current_u FLOAT,
                    current_v FLOAT,
                    PRIMARY KEY (date, lat, lon)
                );
            """)
        conn.commit()
        print("Table created.")
    except psycopg2.Error as e:
        print(f"Failed to create table: {e}")
        raise

def snap(value, resolution=0.25):
    return round(round(value / resolution) * resolution, 2)

def insert_records(conn, ds):
    try:
        ds_loaded = ds.isel(depth=0).load()
        rows = []
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
                        snap(float(lat)),
                        snap(float(lon)),
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
        print(f"{len(rows)} rows")
    except psycopg2.Error as e:
        print(f"Error inserting data: {e}")
        raise

if __name__ == "__main__":
    conn=connect_to_db()
    create_table(conn)
    try:
        for date_start, date_end in YEARS:
            ds=fetch_copernicus(date_start, date_end)
            insert_records(conn, ds)
            time.sleep(3)
    finally:
        conn.close()