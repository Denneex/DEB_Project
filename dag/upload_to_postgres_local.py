# Import the required modules
from airflow import DAG
from airflow.providers.google.cloud.transfers.local_to_gcs import LocalFilesystemToGCSOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime, timedelta

# Define the default arguments for the dag
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 10, 12),
    #'email': ['airflow@example.com'],
    #'email_on_failure': False,
    #'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the dag
with DAG(
    'upload_csv_files',
    default_args=default_args,
    schedule_interval='@once',
) as dag:

    # Define the task to upload movies_reviews.csv to gcp bucket
    upload_movies_reviews = LocalFilesystemToGCSOperator(
        task_id='upload_movies_reviews',
        src=r'C:\Users\shopinverse\Documents\DATA-ENGINEERING\movie_review.csv', 
        dst='movies_reviews.csv',
        bucket='deb_bucket',
        mime_type='text/csv',
        gcp_conn_id='gcp_conn_id',
    )

    # Define the task to upload log_reviews.csv to gcp bucket
    upload_log_reviews = LocalFilesystemToGCSOperator(
        task_id='upload_log_reviews',
        src=r'C:\Users\shopinverse\Documents\DATA-ENGINEERING\log_reviews - log_reviews.csv', 
        dst='log_reviews.csv',
        bucket='deb_bucket', 
        mime_type='text/csv',
        gcp_conn_id='gcp_conn_id',
    )

    # Define the task to create schema and table in postgres database
    create_schema_table = PostgresOperator(
        task_id='create_schema_table',
        postgres_conn_id='postgre_conn',
        sql="""
            CREATE SCHEMA IF NOT EXISTS deb_schema;
            CREATE TABLE IF NOT EXISTS deb_schema.user_purchase (
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

    # Define the task to upload user_purchase.csv to postgres database
    upload_user_purchase = PostgresOperator(
        task_id='upload_user_purchase',
        postgres_conn_id='postgre_conn', 
        sql="""
            COPY deb_schema.user_purchase FROM E'C:\\Users\\shopinverse\\Documents\\DATA-ENGINEERING\\user_purchase - user_purchase.csv' DELIMITER ',' CSV HEADER;
            """,
    )

    # Define the dependencies between the tasks
    upload_movies_reviews >> upload_log_reviews >> create_schema_table >> upload_user_purchase

