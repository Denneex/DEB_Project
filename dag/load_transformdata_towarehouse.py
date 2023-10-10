from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta

# Define the default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 10, 10),
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

# DAG for loading the transformed datasets into the data warehouse
with DAG('load_dw', default_args=default_args, schedule_interval='@daily') as dag:

    # task to load movie_review.csv file from cloud bucket to BigQuery table
    load_movie_review_task = GCSToBigQueryOperator(
        task_id='load_movie_review_task',
        bucket='bucket_name',
        source_objects=['movie_review.csv'],
        destination_project_dataset_table='dataset_id.movie_review',
        schema_fields=[
            {'name': 'user_id', 'type': 'INTEGER', 'mode': 'REQUIRED'},
            {'name': 'positive_review', 'type': 'INTEGER', 'mode': 'NULLABLE'},
            {'name': 'review_id', 'type': 'INTEGER', 'mode': 'REQUIRED'}
        ],
        write_disposition='WRITE_TRUNCATE',
        create_disposition='CREATE_IF_NEEDED'
    )

    # task to load log_reviews.csv file from cloud bucket to BigQuery table
    load_log_reviews_task = GCSToBigQueryOperator(
        task_id='load_log_reviews_task',
        bucket='bucket_name',
        source_objects=['log_reviews.csv'],
        destination_project_dataset_table='dataset_id.log_reviews',
        schema_fields=[
            {'name': 'log_id', 'type': 'INTEGER', 'mode': 'REQUIRED'},
            {'name': 'log_date', 'type': 'DATE', 'mode': 'REQUIRED'},
            {'name': 'device', 'type': 'STRING', 'mode': 'NULLABLE'},
            {'name': 'os', 'type': 'STRING', 'mode': 'NULLABLE'},
            {'name': 'location', 'type': 'STRING', 'mode': NULLABLE'},
            {'name': browser, type: STRING, mode: NULLABLE},
            {'name': ip, type: STRING, mode: NULLABLE},
            {'name': phone_number, type: STRING, mode: NULLABLE}
        ],
        write_disposition='WRITE_TRUNCATE',
        create_disposition='CREATE_IF_NEEDED'
    )

    # task to load user_purchase.csv file from PostgreSQL DB to BigQuery table
    load_user_purchase_task = PythonOperator(
        task_id='load_user_purchase_task',
        python_callable=load_user_purchase # a custom function to load user_purchase.csv file from PostgreSQL DB to BigQuery table
    )

    # The dependencies between the tasks
    [load_movie_review_task, load_log_reviews_task, load_user_purchase_task]

