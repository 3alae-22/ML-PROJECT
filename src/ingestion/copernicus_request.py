import copernicusmarine

import copernicusmarine

ZONE = {
    "lat_min": 29.25,
    "lat_max": 36.0,
    "lon_min": -15.0,
    "lon_max": -9.0,
}

def fetch_copernicus(date_start, date_end):
    ds = copernicusmarine.open_dataset(
        dataset_id="cmems_mod_glo_phy_my_0.083deg_P1D-m",
        variables=["thetao", "so", "uo", "vo"],
        minimum_longitude=ZONE["lon_min"],
        maximum_longitude=ZONE["lon_max"],
        minimum_latitude=ZONE["lat_min"],
        maximum_latitude=ZONE["lat_max"],
        start_datetime=date_start,
        end_datetime=date_end,
        minimum_depth=0,
        maximum_depth=1,
    )
    return ds

if __name__ == "__main__":
    ds = fetch_copernicus("2023-01-01", "2023-01-31")
    print(ds)
