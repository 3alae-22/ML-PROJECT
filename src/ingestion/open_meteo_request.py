import requests
import numpy as np
import time

lats = [round(x, 2) for x in np.arange(30.0, 33.25, 0.25)]
lons = [round(x, 2) for x in np.arange(-10.0, -9.25, 0.25)]
GRID_POINTS = [(lat, lon) for lat in lats for lon in lons]


def fetch_marine(lat, lon, date_start, date_end, retries=3):
    url = (
        f"https://marine-api.open-meteo.com/v1/marine"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=wave_height_max,wave_period_max,swell_wave_height_max"
        f"&start_date={date_start}&end_date={date_end}"
        f"&timezone=UTC"
    )
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            print(f"Timeout attempt {attempt + 1}/{retries}, retrying...")
            time.sleep(2 ** attempt)
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None
    print(f"Failed after {retries} attempts")
    return None


def is_ocean_point(data):
    values = data["daily"]["wave_height_max"]
    return any(v is not None for v in values)


def fetch_wind(lat, lon, date_start, date_end, retries=3):
    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=wind_speed_10m_max,wind_direction_10m_dominant"
        f"&start_date={date_start}&end_date={date_end}"
        f"&timezone=UTC"
    )
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            print(f"Timeout attempt {attempt + 1}/{retries}, retrying...")
            time.sleep(2 ** attempt)
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None
    print(f"Failed after {retries} attempts")
    return None

if __name__ == "__main__":
    valid = 0
    skipped = 0
    failed = 0

    for lat, lon in GRID_POINTS:
        data_marine = fetch_marine(lat, lon, "2022-01-01", "2023-01-01")
        data_wind = fetch_wind(lat, lon, "2022-01-01", "2023-01-01")

        if data_marine is None or data_wind is None:
            failed += 1
            continue

        if not is_ocean_point(data_marine):
            print(f"SKIP lat={lat}, lon={lon} terre ferme")
            skipped += 1
            continue

        daily_marine = data_marine["daily"]
        daily_wind = data_wind["daily"]
        print(f"lat={lat}, lon={lon}")
        for i, date in enumerate(daily_marine["time"]):
            print(
                f"  {date} | "
                f"wave={daily_marine['wave_height_max'][i]}m | "
                f"swell={daily_marine['swell_wave_height_max'][i]}m | "
                f"wind_speed={daily_wind['wind_speed_10m_max'][i]}km/h | "
                f"wind_dir={daily_wind['wind_direction_10m_dominant'][i]}°"
            )
        valid += 1
        time.sleep(1)

    print(f"Valides  : {valid}")
    print(f"Skipped  : {skipped}")
    print(f"Echecs   : {failed}")