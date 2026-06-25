import pandas as pd
from sqlalchemy import create_engine

def build_features():
    engine = create_engine("postgresql://db_user:db_password@localhost:5000/db")
    df = pd.read_sql_table("table_clean", engine, schema="dev")
    df = df.set_index("date")

    # drop unused columns
    df = df.drop(columns=["quarter", "day_of_week", "swell_height_max"])

    # lag features
    for lag in [1, 2, 3, 7, 14]:
        df[f"lag_{lag}"] = (
            df.groupby(["lat_grid", "lon_grid"])["fishing_hours"]
            .shift(lag)
        )

    # target for each horizon
    for h in range(1, 8):
        df[f"target_h{h}"] = (
            df.groupby(["lat_grid", "lon_grid"])["fishing_hours"]
            .shift(-h)
        )

    df = df.dropna()

    df.to_sql("table_features", engine, schema="dev", if_exists="replace")
    print(f"Saved: {df.shape}")

if __name__ == "__main__":
    build_features()