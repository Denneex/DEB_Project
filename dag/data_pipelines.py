# Import the required modules
from airflow import DAG
from airflow.providers.google.cloud.operators.cloud_storage import GCSListObjectsOperator, GCSDeleteObjectsOperator
from airflow.providers.google.cloud.transfers.gcs_to_postgres import GCSToPostgresOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta

# Define the default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
with DAG(
    dag_id='data_pipeline',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False,
) as dag:

    # List the files in the RAW bucket
    list_raw_files = GCSListObjectsOperator(
        task_id='list_raw_files',
        bucket='deb-bucket',
        prefix='data/'
    )

    # Load the user_purchase.csv file into PostgreSQL
    load_user_purchase = GCSToPostgresOperator(
        task_id='load_user_purchase',
        postgres_conn_id='postgre_conn',
        bucket='deb-bucket',
        object_name='data/user_purchase.csv',
        schema='user_purchase_schema',
        table='user_purchase',
        delimiter=',',
        quotechar='"',
        skip_leading_rows=1,
        autocommit=True,
        gcp_conn_id='gcp_conn_id'
    )

    # Delete the user_purchase.csv file from the RAW bucket
    delete_user_purchase = GCSDeleteObjectsOperator(
        task_id='delete_user_purchase',
        bucket_name='raw_bucket',
        objects=['data/user_purchase.csv'],
        gcp_conn_id='gcp_conn_id'
    )

    # Submit the Spark job to transform the movie_review.csv file
    transform_movie_review = SparkSubmitOperator(
        task_id='transform_movie_review',
        conn_id='spark_default',
        application='/path/to/spark_job.py', # The path to the Python script that contains the transformation logic for movie_review.csv
        application_args=['deb-bucket', 'stage_bucket'], # The names of the input and output buckets as arguments
        name='transform_movie_review'
    )

    # Submit the Spark job to transform the log_reviews.csv file
    transform_log_reviews = SparkSubmitOperator(
        task_id='transform_log_reviews',
        conn_id='spark_default',
        application='/path/to/spark_job.py', # The path to the Python script that contains the transformation logic for log_reviews.csv
        application_args=['raw_bucket', 'stage_bucket'], # The names of the input and output buckets as arguments
        name='transform_log_reviews'
    )

    # Download the user_purchase table from PostgreSQL and store it in the STAGE bucket
    download_user_purchase = PostgresOperator(
        task_id='download_user_purchase',
        postgres_conn_id='postgre_conn',
        sql="""
            COPY user_purchase_schema.user_purchase TO '/tmp/user_purchase.csv' DELIMITER ',' CSV HEADER;
            """,
        autocommit=True
    )

    upload_user_purchase = GCSUploadObjectOperator(
        task_id='upload_user_purchase',
        bucket_name='deb-bucket',
        object_name='data/user_purchase.csv',
        filename='/tmp/user_purchase.csv',
        gcp_conn_id='gcp_conn_id'
    )

    # Define the dependencies between the tasks
    list_raw_files >> load_user_purchase >> delete_user_purchase >> download_user_purchase >> upload_user_purchase
    list_raw_files >> transform_movie_review
    list_raw_files >> transform_log_reviews