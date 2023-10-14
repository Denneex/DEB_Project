# Import the required modules
from airflow import DAG
from airflow.providers.google.cloud.operators.cloud_storage import GCSListObjectsOperator, GCSDeleteObjectsOperator
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.providers.google.cloud.transfers.bigquery_to_gcs import BigQueryToGCSOperator
from airflow.providers.google.cloud.hooks.bigquery import BigQueryHook
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

    # List the files in the STAGE bucket
    list_stage_files = GCSListObjectsOperator(
        task_id='list_stage_files',
        bucket='deb-bucket',
        prefix='data/'
    )

    # Load the user_purchase.csv file into BigQuery
    load_user_purchase = GCSToBigQueryOperator(
        task_id='load_user_purchase',
        bucket='deb-bucket',
        source_objects=['data/user_purchase.csv'],
        destination_project_dataset_table='user_purchase_schema.user_purchase',
        schema_fields=[
            {'name': 'invoice_number', 'type': 'STRING', 'mode': 'NULLABLE'},
            {'name': 'stock_code', 'type': 'STRING', 'mode': 'NULLABLE'},
            {'name': 'detail', 'type': 'STRING', 'mode': 'NULLABLE'},
            {'name': 'quantity', 'type': 'INTEGER', 'mode': 'NULLABLE'},
            {'name': 'invoice_date', 'type': 'TIMESTAMP', 'mode': 'NULLABLE'},
            {'name': 'unit_price', 'type': 'NUMERIC', 'mode': 'NULLABLE'},
            {'name': 'customer_id', 'type': 'INTEGER', 'mode': 'NULLABLE'},
            {'name': 'country', 'type': 'STRING', 'mode': 'NULLABLE'}
        ],
        write_disposition='WRITE_TRUNCATE',
        autodetect=False,
        skip_leading_rows=1,
        gcp_conn_id='gcp_conn_id'
    )

    # Load the movie_review.csv file into BigQuery
    load_movie_review = GCSToBigQueryOperator(
        task_id='load_movie_review',
        bucket='deb-bucket',
        source_objects=['data/movie_review.csv'],
        destination_project_dataset_table='user_purchase_schema.movie_review',
        schema_fields=[
            {'name': 'user_id', 'type': 'INTEGER', 'mode': 'NULLABLE'},
            {'name': 'positive_review', type: 'INTEGER', 'mode': 'NULLABLE'},
            {'name': 'review_id', type: 'STRING', 'mode': 'NULLABLE'}
        ],
        write_disposition='WRITE_TRUNCATE',
        autodetect=False,
        skip_leading_rows=1,
        gcp_conn_id='gcp_conn_id'
    )

    # Load the log_reviews.csv file into BigQuery
    load_log_reviews = GCSToBigQueryOperator(
        task_id='load_log_reviews',
        bucket='deb-bucket',
        source_objects=['data/log_reviews.csv'],
        destination_project_dataset_table='user_purchase_schema.log_reviews',
        schema_fields=[
            {'name': 'log_id', type: 'STRING', 'mode': 'NULLABLE'},
            {'name': 'log_date', type: 'TIMESTAMP', 'mode': 'NULLABLE'},
            {'name': 'device', type: 'STRING', 'mode': 'NULLABLE'},
            {'name': 'os', type: 'STRING', 'mode': 'NULLABLE'},
            {'name': 'location', type: 'STRING', 'mode': 'NULLABLE'},
            {'name': 'browser', type: 'STRING', 'mode': 'NULLABLE'},
            {'name': 'ip', type: 'STRING', 'mode': 'NULLABLE'},
            {'name': 'phone_number', type: 'STRING', 'mode': 'NULLABLE'}
        ],
        write_disposition='WRITE_TRUNCATE',
        autodetect=False,
        skip_leading_rows=1,
        gcp_conn_id='gcp_conn_id'
    )

    # Create the dim_date table in BigQuery
    create_dim_date = BigQueryOperator(
        task_id='create_dim_date',
        sql="""
            CREATE TABLE IF NOT EXISTS user_purchase_schema.dim_date AS
            SELECT DISTINCT 
                CAST(FORMAT_DATE('%Y%m%d', log_date) AS INT64) AS id_dim_date,
                log_date AS log_date,
                FORMAT_DATE('%A', log_date) AS day,
                FORMAT_DATE('%B', log_date) AS month,
                FORMAT_DATE('%Y', log_date) AS year,
                CASE
                    WHEN FORMAT_DATE('%m', log_date) IN ('12', '01', '02') THEN 'Winter'
                    WHEN FORMAT_DATE('%m', log_date) IN ('03', '04', '05') THEN 'Spring'
                    WHEN FORMAT_DATE('%m', log_date) IN ('06', '07', '08') THEN 'Summer'
                    ELSE 'Fall'
                END AS season
            FROM user_purchase_schema.log_reviews;
            """,
        use_legacy_sql=False,
        gcp_conn_id='gcp_conn_id',
        bigquery_conn_id='bigquery_default'
    )

    # Create the dim_devices table in BigQuery
    create_dim_devices = BigQueryOperator(
        task_id='create_dim_devices',
        sql="""
            CREATE TABLE IF NOT EXISTS user_purchase_schema.dim_devices AS
            SELECT DISTINCT 
                ROW_NUMBER() OVER (ORDER BY device) AS id_dim_devices,
                device AS device
            FROM user_purchase_schema.log_reviews;
            """,
        use_legacy_sql=False,
        gcp_conn_id='gcp_conn_id',
        bigquery_conn_id='bigquery_default'
    )

    # Create the dim_location table in BigQuery
    create_dim_location = BigQueryOperator(
        task_id='create_dim_location',
        sql="""
            CREATE TABLE IF NOT EXISTS user_purchase_schema.dim_location AS
            SELECT DISTINCT 
                ROW_NUMBER() OVER (ORDER BY location) AS id_dim_location,
                location AS location
            FROM user_purchase_schema.log_reviews;
            """,
        use_legacy_sql=False,
        gcp_conn_id='gcp_conn_id',
        bigquery_conn_id='bigquery_default'
    )

    # Create the dim_os table in BigQuery
    create_dim_os = BigQueryOperator(
        task_id='create_dim_os',
        sql="""
            CREATE TABLE IF NOT EXISTS user_purchase_schema.dim_os AS
            SELECT DISTINCT 
                ROW_NUMBER() OVER (ORDER BY os) AS id_dim_os,
                os AS os
            FROM user_purchase_schema.log_reviews;
            """,
        use_legacy_sql=False,
        gcp_conn_id='gcp_conn_id',
        bigquery_conn_id='bigquery_default'
    )

    # Create the dim_browser table in BigQuery
    create_dim_browser = BigQueryOperator(
        task_id='create_dim_browser',
        sql="""
            CREATE TABLE IF NOT EXISTS user_purchase_schema.dim_browser AS
            SELECT DISTINCT 
                ROW_NUMBER() OVER (ORDER BY browser) AS id_dim_browser,
                browser AS browser
            FROM user_purchase_schema.log_reviews;
            """,
        use_legacy_sql=False,
        gcp_conn_id='gcp_conn_id',
        bigquery_conn_id='bigquery_default'
    )

    # Create the fact_movie_analytics table in BigQuery
    create_fact_movie_analytics = BigQueryOperator(
        task_id='create_fact_movie_analytics',
        sql="""
            CREATE TABLE IF NOT EXISTS user_purchase_schema.fact_movie_analytics AS
            SELECT 
                up.customer_id AS customerid,
                dd.id_dim_devices AS id_dim_devices,
                dl.id_dim_location AS id_dim_location,
                do.id_dim_os AS id_dim_os,
                db.id_dim_browser AS id_dim_browser,
                SUM(up.quantity * up.unit_price) AS amount_spent,
                SUM(mr.positive_review) AS review_score,
                COUNT(mr.review_id) AS review_count,
                CURRENT_DATE() AS insert_date
            FROM user_purchase_schema.user_purchase up
            JOIN user_purchase_schema.movie_review mr ON up.customer_id = mr.user_id
            JOIN user_purchase_schema.log_reviews lr ON mr.review_id = lr.log_id
            JOIN user_purchase_schema.dim_date dd ON lr.log_date = dd.log_date
            JOIN user_purchase_schema.dim_devices dd ON lr.device = dd.device
            JOIN user_purchase_schema.dim_location dl ON lr.location = dl.location
            JOIN user_purchase_schema.dim_os do ON lr.os = do.os
            JOIN user_purchase_schema.dim_browser db ON lr.browser = db.browser
            GROUP BY customerid, id_dim_devices, id_dim_location, id_dim_os, id_dim_browser;
            """,
        use_legacy_sql=False,
        gcp_conn_id='gcp_conn_id',
        bigquery_conn_id='bigquery_default'
    )

    # Export the fact_movie_analytics table to the DW bucket as a CSV file
    export_fact_movie_analytics = BigQueryToGCSOperator(
        task_id='export_fact_movie_analytics',
        source_project_dataset_table='user_purchase_schema.fact_movie_analytics',
        destination_cloud_storage_uris=['gs://dw_bucket/data/fact_movie_analytics.csv'],
        export_format='CSV',
        print_header=True,
        gcp_conn_id='gcp_conn_id',
        bigquery_conn_id='bigquery_default'
    )

    # Define the dependencies between the tasks
    list_stage_files >> [load_user_purchase, load_movie_review, load_log_reviews]