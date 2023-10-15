# Import the required modules
from airflow import DAG
from airflow.providers.google.cloud.hooks.gcs import GCSHook
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
    #'email': ['airflow@example.com'],
    #'email_on_failure': False,
    #'email_on_retry': False,
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

    # Create a GCSHook instance
    gcs_hook = GCSHook(gcp_conn_id='gcp_conn_id')

    # List the files in the RAW bucket
    list_raw_files = gcs_hook.list(bucket_name='deb-bucket', prefix='data/')

    # Create the user_purchase_schema in PostgreSQL
    create_user_purchase_schema = PostgresOperator(
        task_id='create_user_purchase_schema',
        postgres_conn_id='postgre_conn',
        sql="""
            CREATE SCHEMA IF NOT EXISTS user_purchase_schema;
            """,
        autocommit=True
    )

    # Create the user_purchase table in PostgreSQL
    create_user_purchase_table = PostgresOperator(
        task_id='create_user_purchase_table',
        postgres_conn_id='postgre_conn',
        sql="""
            CREATE TABLE IF NOT EXISTS user_purchase_schema.user_purchase (
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
        autocommit=True
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

    # Create a temporary file object for the user_purchase.csv file
    user_purchase_file = gcs_hook.download(bucket_name='deb-bucket', object_name='data/user_purchase.csv')

    # Delete the user_purchase.csv file from the RAW bucket
    delete_user_purchase = gcs_hook.delete(bucket_name='deb-bucket', objects=['data/user_purchase.csv'])

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
        application_args=['deb-bucket', 'stage_bucket'], # The names of the input and output buckets as arguments
        name='transform_log_reviews'
    )

    # Download the user_purchase table from PostgreSQL and store it in the STAGE bucket using PostgresToGCSOperator
    download_user_purchase = PostgresToGCSOperator(
        task_id='download_user_purchase',
        postgres_conn_id='postgre_conn',
        bucket='stage_bucket',
        filename='user_purchase.csv',
        sql="""
            SELECT * FROM user_purchase_schema.user_purchase;
            """,
        schema_filename=None,
        export_format="CSV",
        field_delimiter=',',
        print_header=True,
        gcp_conn_id='gcp_conn_id'
    )

    # Define the dependencies between the tasks
    list_raw_files >> create_user_purchase_schema >> create_user_purchase_table >> load_user_purchase >> delete_user_purchase >> download_user_purchase
    list_raw_files >> transform_movie_review
    list_raw_files >> transform_log_reviews
