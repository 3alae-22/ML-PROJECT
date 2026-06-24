import pandas as pd
from sqlalchemy import create_engine

def run_cleaning():
    engine = create_engine("postgresql://db_user:db_password@localhost:5000/db")

    # load
    df = pd.read_sql_table("mrt_table", engine, schema="dev").set_index("date")
    print(f"Loaded: {df.shape}")

    # drop always/sometimes null cells (spatial nulls)
    total_dates = df.groupby("date").size().shape[0]
    null_cells = df[df["sst"].isna()][["lat_grid", "lon_grid"]].value_counts()

    cells_to_drop = null_cells.index  # drop all -> always + sometimes
    df = df[~df.set_index(["lat_grid", "lon_grid"]).index.isin(cells_to_drop)].copy()
    print(f"After spatial drop: {df.shape}")

    # interpolate temporal nulls in wave_period_max
    df["wave_period_max"] = (
        df.groupby(["lat_grid", "lon_grid"])["wave_period_max"]
        .transform(lambda x: x.interpolate(method="time"))
    )
    print(f"Remaining nulls: {df.isna().sum().sum()}")

    # save
    df.to_sql("table_clean", engine, schema="dev", if_exists="replace")
    print(f"Saved: {df.shape}")

if __name__ == "__main__":
    run_cleaning()