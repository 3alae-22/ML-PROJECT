import requests
import numpy as np
import time
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")


def fetch_gfw(date_start, date_end):
    url = "https://gateway.api.globalfishingwatch.org/v3/4wings/report"
    params = {
        "spatial-resolution": "HIGH",
        "temporal-resolution": "DAILY",
        "group-by": "GEARTYPE",            
        "datasets[0]": "public-global-fishing-effort:latest",
        "date-range": f"{date_start},{date_end}",
        "format": "JSON"
    }
    body = {
        "geojson": {
            "type": "Polygon",
            "coordinates": [[
                [-10.0, 30.0],
                [-10.0, 33.0],
                [-9.5,  33.0],
                [-9.5,  30.0],
                [-10.0, 30.0]
            ]]
        }
    }
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        response = requests.post(url, params=params, json=body, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None

if __name__ == "__main__":
    YEARS = [
        ("2023-01-01", "2023-12-31"),
        ("2024-01-01", "2024-12-31"),
        ("2025-01-01", "2025-12-31"),
    ]

    for date_start, date_end in YEARS:
        data=fetch_gfw(date_start, date_end)
        print(data)