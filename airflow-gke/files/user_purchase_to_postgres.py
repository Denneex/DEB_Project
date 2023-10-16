# Import the required modules
from airflow.models import DAG
from airflow.operators.dummy import DummyOperator
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.providers.google.cloud.sensors.gcs import GCSObjectExistenceSensor
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
import os
from datetime import datetime, timedelta

# General constants
DAG_ID = "upload_csv_files"
STABILITY_STATE = "unstable"
CLOUD_PROVIDER = "gcp"

# GCP constants
GCP_CONN_ID = "gcp_conn_id"
GCS_BUCKET_NAME = "deb-bucket"
GCS_KEY_NAME = "user_purchase - user_purchase.csv"

# Postgres constants
POSTGRES_CONN_ID = "postgre_conn"
POSTGRES_TABLE_NAME = "user_purchase"


def ingest_data_from_gcs(
    gcs_bucket: str,
    gcs_object: str,
    postgres_table: str,
    gcp_conn_id: str = "gcp_conn_id",
    postgres_conn_id: str = "postgre_conn",
):
    """Ingest data from an GCS location into a postgres table.

    Args:
        gcs_bucket (str): Name of the bucket.
        gcs_object (str): Name of the object.
        postgres_table (str): Name of the postgres table.
        gcp_conn_id (str): Name of the Google Cloud connection ID.
        postgres_conn_id (str): Name of the postgres connection ID.
    """
    import tempfile

    gcs_hook = GCSHook(gcp_conn_id=gcp_conn_id)
    psql_hook = PostgresHook(postgres_conn_id)

    with tempfile.NamedTemporaryFile() as tmp:
        gcs_hook.download(
            bucket_name=gcs_bucket, object_name=gcs_object, filename=tmp.name
        )
        psql_hook.bulk_load(table=postgres_table, tmp_file=tmp.name)


with DAG(
    dag_id=DAG_ID,
    schedule_interval="@once",
    start_date=days_ago(1),
    tags=[CLOUD_PROVIDER, STABILITY_STATE],
) as dag:
    start_workflow = DummyOperator(task_id="start_workflow")

    verify_key_existence = GCSObjectExistenceSensor(
        task_id="verify_key_existence",
        google_cloud_conn_id=GCP_CONN_ID,
        bucket=GCS_BUCKET_NAME,
        object=GCS_KEY_NAME,
    )

    create_table_entity = PostgresOperator(
        task_id="create_table_entity",
        postgres_conn_id=POSTGRES_CONN_ID,
        sql=f"""
            CREATE SCHEMA IF NOT EXISTS deb_schema;
            CREATE TABLE IF NOT EXISTS deb_schema.{POSTGRES_TABLE_NAME} (
                invoice_number varchar(10),
                stock_code varchar(20),
                detail varchar(1000),
                quantity int,
                invoice_date timestamp,
                unit_price numeric(8,3),
                customer_id int,
                country varchar(20)
            );
            """,
    )

    clear_table = PostgresOperator(
        task_id="clear_table",
        postgres_conn_id=POSTGRES_CONN_ID,
        sql=f"DELETE FROM deb_schema.{POSTGRES_TABLE_NAME}",
    )
    
    ingest_data = PythonOperator(
        task_id="ingest_data",
        python_callable=ingest_data_from_gcs,
        op_kwargs={
            "gcs_bucket": GCS_BUCKET_NAME,
            "gcs_object": GCS_KEY_NAME,
            "postgres_table": POSTGRES_TABLE_NAME,
            "gcp_conn_id": GCP_CONN_ID,
            "postgres_conn_id": POSTGRES_CONN_ID,
        },
    )

    end_workflow = DummyOperator(task_id="end_workflow")

# Define the workflow dependencies
start_workflow >> verify_key_existence >> create_table_entity >> clear_table >> ingest_data >> end_workflow

