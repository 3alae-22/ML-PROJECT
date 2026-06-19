from open_meteo_request import fetch_data
import psycopg2

def connect_to_db():
    print("connecting to the PostgreSQL database ...")
    try:
        conn=psycopg2.connect(
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
    print("Creating table if not exist ...")
    try:
        with conn.cursor() as cursor:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS dev;")      
            cursor.execute("""
                CREATE SCHEMA IF NOT EXISTS dev;
                CREATE TABLE IF NOT EXISTS dev.raw_weather_data(
                    datetime TIMESTAMP PRIMARY KEY,
                    temperature FLOAT,
                    apparent_temperature FLOAT,
                    cloud_cover FLOAT,
                    relative_humidity FLOAT,
                    wind_speed FLOAT,
                    wind_direction FLOAT,
                    precipitation FLOAT,
                    pressure_msl FLOAT
                );
            """
            )
        conn.commit()
        print("Table was created")
    except psycopg2.Error as e:
        print(f"Failed to create table: {e}")
        raise

conn=connect_to_db()
create_table(conn)

def insert_reords(conn, data):
    print("Inserting weather data into the database ...")
    try:
        with conn.cursor() as cursor:
            feature=data["hourly"]
            cursor.execute("""
                INSERT INTO dev.raw_weather_data(
                    datetime,
                    temperature,
                    apparent_temperature,
                    cloud_cover,
                    relative_humidity,
                    wind_speed,
                    wind_direction,
                    precipitation,
                    pressure_msl           
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) 
            """,(
                feature["time"],
                feature["temperature_2m"],
                feature["apparent_temperature"],
                feature["cloud_cover"],
                feature["relative_humidity_2m"],
                feature["wind_speed_10m"],
                feature["wind_direction_10m"],
                feature["precipitation"],
                feature["pressure_msl"],
                

            ))

    except:
