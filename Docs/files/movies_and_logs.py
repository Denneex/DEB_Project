# Import the required modules
from airflow import DAG
from airflow.providers.google.cloud.transfers.local_to_gcs import LocalFilesystemToGCSOperator
from datetime import datetime, timedelta

# Define the default arguments for the dag
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 10, 13),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the dag
with DAG(
    'upload_csv_files_to_gcp',
    default_args=default_args,
    schedule_interval='@once',
) as dag:

    # Define the task to upload movies_reviews.csv to gcp bucket
    upload_movies_reviews = LocalFilesystemToGCSOperator(
        task_id='upload_movies_reviews',
        src=r'C:\Users\shopinverse\Documents\DATA-ENGINEERING\movie_review.csv', 
        dst='movies_reviews.csv',
        bucket='deb-bucket',
        mime_type='text/csv',
        gcp_conn_id='gcp_conn_id',
    )

    # Define the task to upload log_reviews.csv to gcp bucket
    upload_log_reviews = LocalFilesystemToGCSOperator(
        task_id='upload_log_reviews',
        src=r'C:\Users\shopinverse\Documents\DATA-ENGINEERING\log_reviews - log_reviews.csv', 
        dst='log_reviews.csv',
        bucket='deb-bucket', 
        mime_type='text/csv',
        gcp_conn_id='gcp_conn_id',
    )

    # Define the dependencies between the tasks
    upload_movies_reviews >> upload_log_reviews
