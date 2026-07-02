import pandas as pd
import numpy as np
from sqlalchemy import create_engine


def build_features():
    engine = create_engine("postgresql://db_user:db_password@localhost:5000/db")
    df = pd.read_sql_table("table_clean", engine, schema="dev")
    df = df.sort_values(["date", "lat_grid", "lon_grid"]).reset_index(drop=True)

    # drop unused columns
    df = df.drop(columns=["quarter", "day_of_week", "swell_height_max"], errors="ignore")

    # lag features
    for lag in [1, 2, 3, 7, 14, 365]:
        df[f"lag_{lag}"] = (
            df.groupby(["lat_grid", "lon_grid"])["fishing_hours"]
            .shift(lag)
        )

    # rolling statistics per cell (shift(1) to avoid leakage)
    for window in [7, 14]:
        df[f"rolling_mean_{window}"] = (
            df.groupby(["lat_grid", "lon_grid"])["fishing_hours"]
            .transform(lambda x: x.shift(1).rolling(window).mean())
        )
        df[f"rolling_std_{window}"] = (
            df.groupby(["lat_grid", "lon_grid"])["fishing_hours"]
            .transform(lambda x: x.shift(1).rolling(window).std())
        )
        df[f"rolling_max_{window}"] = (
            df.groupby(["lat_grid", "lon_grid"])["fishing_hours"]
            .transform(lambda x: x.shift(1).rolling(window).max())
        )

    # target for each horizon
    for h in range(1, 8):
        df[f"target_h{h}"] = (
            df.groupby(["lat_grid", "lon_grid"])["fishing_hours"]
            .shift(-h)
        )

    df = df.dropna()

    df.to_sql("table_features", engine, schema="dev",
              if_exists="replace", index=False)
    print(f"Saved table_features: {df.shape}")


if __name__ == "__main__":
    build_features()