# Import the required modules
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.google.cloud.transfers.gcs_to_local import GCSToLocalFilesystemOperator
from pyspark.sql import SparkSession
from pyspark.ml.feature import Tokenizer, StopWordsRemover
import databricks.spark.xml as spark_xml

# Define the default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 10, 10),
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

# Define the DAG
with DAG('data_pipeline', default_args=default_args, schedule_interval='@daily') as dag:

    # task to execute Terraform template for CI/CD
    terraform_task = PythonOperator(
        task_id='terraform_task',
        python_callable=execute_terraform_template # a custom function to execute the Terraform template
    )

    # task to create PostgreSQL DB and table using schema
    create_db_task = PostgresOperator(
        task_id='create_db_task',
        postgres_conn_id='postgres_default',
        sql='''
        CREATE SCHEMA IF NOT EXISTS schema_name;
        CREATE TABLE IF NOT EXISTS schema_name.user_purchase (
            invoice_number varchar(10),
            stock_code varchar(20),
            detail varchar(1000),
            quantity int,
            invoice_date timestamp,
            unit_price numeric(8,3),
            customer_id int,
            country varchar(20)
        );
        '''
    )

    # task to load user_purchase.csv file into PostgreSQL DB
    load_db_task = PostgresOperator(
        task_id='load_db_task',
        postgres_conn_id='postgres_default',
        sql='''
        COPY schema_name.user_purchase FROM '/path/to/user_purchase.csv' DELIMITER ',' CSV HEADER;
        '''
    )

    # task to download movie_review.csv and log_reviews.csv files from cloud bucket to local filesystem
    download_files_task = GCSToLocalFilesystemOperator(
        task_id='download_files_task',
        bucket='bucket_name',
        object_name='movie_review.csv,log_reviews.csv',
        filename='/path/to/local/filesystem'
    )

    # task to transform movie_review.csv file using pyspark
    transform_movie_review_task = PythonOperator(
        task_id='transform_movie_review_task',
        python_callable=transform_movie_review # a custom function to transform movie_review.csv file using pyspark
    )

    # task to transform log_reviews.csv file using pyspark and databricks.spark.xml library
    transform_log_reviews_task = PythonOperator(
        task_id='transform_log_reviews_task',
        python_callable=transform_log_reviews # a custom function to transform log_reviews.csv file using pyspark and databricks.spark.xml library
    )

    # task to load the transformed data into DW using Terraform template
    load_dw_task = PythonOperator(
        task_id='load_dw_task',
        python_callable=load_dw 
    )

# Set the dependencies between the tasks
terraform_task >> create_db_task >> load_db_task >> download_files_task >> [transform_movie_review_task, transform_log_reviews_task] >> load_dw_task

