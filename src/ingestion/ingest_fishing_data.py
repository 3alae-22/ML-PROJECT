import psycopg2
import time
from gfw_request import fetch_gfw

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
                CREATE TABLE IF NOT EXISTS dev.raw_fishing(
                    date DATE,
                    lat FLOAT,
                    lon FLOAT,
                    lat_grid FLOAT,
                    lon_grid FLOAT,
                    hours FLOAT,
                    geartype VARCHAR(50),
                    vessel_ids  INT,
                    PRIMARY KEY (date, lat, lon, geartype)
                );
            """)
        conn.commit()
        print("Table created.")
    except psycopg2.Error as e:
        print(f"Failed to create table: {e}")
        raise

def snap(value, resolution=0.25):
    return round(round(value / resolution) * resolution, 2)

def insert_records(conn, data):
    try:
        with conn.cursor() as cursor:
            rows = [
                (
                    entry["date"],
                    entry["lat"],
                    entry["lon"],
                    snap(entry["lat"]),
                    snap(entry["lon"]),
                    entry["hours"],
                    entry["geartype"],
                    entry["vesselIDs"],
                )
                for entry in data
            ]

            cursor.executemany("""
                INSERT INTO dev.raw_fishing(
                    date, lat, lon, lat_grid, lon_grid,
                    hours, geartype, vessel_ids       
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (date, lat, lon, geartype) DO NOTHING;
            """,rows)
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
            data=fetch_gfw(date_start, date_end)
            records = data["entries"][0]["public-global-fishing-effort:v4.0"]
            insert_records(conn, records)
            time.sleep(3)
    finally:
        conn.close()