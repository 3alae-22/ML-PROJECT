import requests


lat = 45.46305
lon = 9.19581

api_url = (
    f"https://archive-api.open-meteo.com/v1/archive"
    f"?latitude={lat}&longitude={lon}"
    f"&start_date=2018-01-01&end_date=2018-01-02"
    f"&hourly=temperature_2m,apparent_temperature,cloud_cover,relative_humidity_2m,windspeed_10m,wind_direction_10m,precipitation,pressure_msl"
)

def fetch_data():
    print("Fetching weather data from open-meteo ...")
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        print("API response received successfuly.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"An error occured: {e}")
        raise

if __name__ == "__main__":
    data = fetch_data()
    print(data)

    