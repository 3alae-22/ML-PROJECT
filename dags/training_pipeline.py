from airflow.sdk import dag, task
from datetime import datetime, timedelta

default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
}

@dag(
    dag_id='training_pipeline',
    schedule='@weekly',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=['fishing', 'training'],
)
def training_pipeline():

    @task
    def train_and_register():
        from src.training.train_and_register import train_and_register as _train
        _train()
        return {"status": "trained"}

    @task
    def promote_to_production():
        import mlflow
        from mlflow.tracking import MlflowClient

        mlflow.set_tracking_uri("http://mlflow_container:5001")
        client = MlflowClient()

        for H in range(1, 8):
            model_name = f"fishing_2stage_J{H}"
            try:
                versions = client.search_model_versions(
                    filter_string=f"name='{model_name}'",
                    order_by=["version_number DESC"],
                    max_results=1,
                )
                if versions:
                    client.set_registered_model_alias(
                        name=model_name,
                        alias="champion",
                        version=versions[0].version,
                    )
                    print(f"J+{H} v{versions[0].version} → champion")
            except Exception as e:
                print(f"Warning J+{H}: {e}")

        return {"status": "promoted"}

    train = train_and_register()
    promote = promote_to_production()

    train >> promote


training_pipeline()