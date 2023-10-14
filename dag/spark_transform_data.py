from pyspark.sql import SparkSession
from pyspark.sql.functions import col, split, explode, when, current_timestamp
from pyspark.ml.feature import Tokenizer, StopWordsRemover

# Create a Spark session
spark = SparkSession.builder.appName("Data Transformation").getOrCreate()

# Read the movie_review.csv file from the RAW bucket
movie_review = spark.read.format("csv").option("header", "true").load("gs://raw_bucket/data/movie_review.csv")

# Tokenize the review_str column
tokenizer = Tokenizer(inputCol="review_str", outputCol="review_token")
movie_review = tokenizer.transform(movie_review)

# Remove stop words from the review_token column
remover = StopWordsRemover(inputCol="review_token", outputCol="review_clean")
movie_review = remover.transform(movie_review)

# Filter the data that contain the word "good"
movie_review = movie_review.filter(explode(col("review_clean")).alias("word") == "good")

# Add a positive_review column with value 1
movie_review = movie_review.withColumn("positive_review", when(col("word") == "good", 1))

# Add an insert_date column with the current timestamp
movie_review = movie_review.withColumn("insert_date", current_timestamp())

# Select the user_id, positive_review and review_id columns
movie_review = movie_review.select("user_id", "positive_review", "review_id")

# Write the output to the STAGE bucket as a parquet file
movie_review.write.format("parquet").mode("overwrite").save("gs://stage_bucket/data/movie_review.parquet")

# Read the log_reviews.csv file from the RAW bucket
log_reviews = spark.read.format("xml").option("rowTag", "log").load("gs://raw_bucket/data/log_reviews.csv")

# Parse the log column to get the metadata
log_reviews = log_reviews.select(
    col("_id").alias("log_id"),
    col("_date").alias("log_date"),
    col("_device").alias("device"),
    col("_os").alias("os"),
    col("_location").alias("location"),
    col("_browser").alias("browser"),
    col("_ip").alias("ip"),
    col("_phone_number").alias("phone_number")
)

# Write the output to the STAGE bucket as a parquet file
log_reviews.write.format("parquet").mode("overwrite").save("gs://stage_bucket/data/log_reviews.parquet")
