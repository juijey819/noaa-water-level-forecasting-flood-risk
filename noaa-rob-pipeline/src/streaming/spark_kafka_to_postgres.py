"""
Spark Structured Streaming consumer for NOAA water level stream.

Final streaming path:
NOAA API -> Python Producer -> Kafka topic noaa_water_level_raw
-> Spark Structured Streaming -> PostgreSQL -> Dashboard.

Spark is used as the main Kafka consumer and stream processor.
"""

import os, json
from datetime import datetime

import requests as http
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    from_json,
    to_timestamp,
    current_timestamp,
    lit,
    window,
    last,
    avg,
    max as spark_max,
    min as spark_min,
    stddev,
    count,
    when,
)
from pyspark.sql.types import StructType, StructField, StringType, DoubleType


def jdbc_url():
    return (
        f"jdbc:postgresql://{os.getenv('POSTGRES_HOST', 'postgres')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'noaa_rob')}"
    )


def jdbc_props():
    return {
        "user": os.getenv("POSTGRES_USER", "noaa_user"),
        "password": os.getenv("POSTGRES_PASSWORD", "noaa_password"),
        "driver": "org.postgresql.Driver",
    }


def send_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    try:
        r = http.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": message}, timeout=15)
        r.raise_for_status()
        return True
    except Exception:
        return False


def write_log(spark, run_id, task_name, severity, status, message, records_processed=0, error_detail=None):
    rows = [(
        run_id,
        "stream_noaa_water_level",
        "spark_structured_streaming",
        task_name,
        severity,
        status,
        message,
        int(records_processed or 0),
        error_detail,
        datetime.utcnow(),
    )]

    schema = """
        run_id STRING,
        pipeline_name STRING,
        component STRING,
        task_name STRING,
        severity STRING,
        status STRING,
        message STRING,
        records_processed INT,
        error_detail STRING,
        event_time TIMESTAMP
    """

    df = spark.createDataFrame(rows, schema=schema)
    df.write.jdbc(
        url=jdbc_url(),
        table="pipeline_execution_log",
        mode="append",
        properties=jdbc_props(),
    )


def write_raw_batch(batch_df, batch_id):
    spark = batch_df.sparkSession
    run_id = f"spark_raw_batch_{batch_id}"

    if batch_df.rdd.isEmpty():
        write_log(spark, run_id, "write_raw_stream", "DEBUG", "SUCCESS", "Empty micro-batch.", 0)
        return

    out = (
        batch_df.select(
            col("station_id"),
            col("station_name"),
            col("observation_time"),
            col("water_level_m"),
            col("sigma"),
            col("data_flags"),
            col("datum"),
            col("source_product"),
            col("kafka_topic"),
            col("kafka_partition"),
            col("kafka_offset"),
        )
        .dropDuplicates(["station_id", "observation_time", "source_product"])
    )

    count_rows = out.count()
    print(f"[Spark] write_raw_batch: {count_rows} rows")

    out.write.jdbc(
        url=jdbc_url(),
        table="raw_noaa_water_level_stream",
        mode="append",
        properties=jdbc_props(),
    )

    write_log(
        spark,
        run_id,
        "write_raw_stream",
        "INFO",
        "SUCCESS",
        f"Spark wrote {count_rows} raw stream rows to PostgreSQL.",
        count_rows,
    )

    for row in out.collect():
        r = row.asDict()
        risk = "NORMAL"
        wl = r["water_level_m"]
        if wl >= 1.204: risk = "MAJOR"
        elif wl >= 0.825: risk = "MODERATE"
        elif wl >= 0.534: risk = "MINOR"
        flag = r.get("data_flags")
        msg = (f"\U0001F30A [NOAA Stream] Station {r['station_id']}\n"
               f"Time: {r['observation_time']}\n"
               f"Water Level: {wl:.3f} m\n"
               f"Risk: {risk}\n"
               f"Sigma: {r.get('sigma', 'N/A')}\n"
               f"Flags: {flag if flag and flag != '0,0' else 'None'}")
        send_telegram(msg)


def write_hourly_batch(batch_df, batch_id):
    spark = batch_df.sparkSession
    run_id = f"spark_hourly_batch_{batch_id}"

    if batch_df.rdd.isEmpty():
        write_log(spark, run_id, "write_hourly_aggregation", "DEBUG", "SUCCESS", "Empty hourly micro-batch.", 0)
        return

    hourly = (
        batch_df
        .groupBy(
            col("station_id"),
            window(col("observation_time"), "1 hour").alias("w")
        )
        .agg(
            last("water_level_m").alias("hourly_last_water_level_m"),
            avg("water_level_m").alias("hourly_mean_water_level_m"),
            spark_max("water_level_m").alias("hourly_max_water_level_m"),
            spark_min("water_level_m").alias("hourly_min_water_level_m"),
            stddev("water_level_m").alias("hourly_std_water_level_m"),
            count("water_level_m").alias("record_count"),
        )
        .select(
            col("station_id"),
            col("w.start").alias("hour_timestamp"),
            col("hourly_last_water_level_m"),
            col("hourly_mean_water_level_m"),
            col("hourly_max_water_level_m"),
            col("hourly_min_water_level_m"),
            col("hourly_std_water_level_m"),
            col("record_count"),
            ((col("hourly_max_water_level_m") - col("hourly_min_water_level_m")) > lit(0.30)).alias("spike_flag"),
            current_timestamp().alias("created_at"),
        )
    )

    count_rows = hourly.count()
    print(f"[Spark] write_hourly_batch: {count_rows} hourly rows")

    hourly.write.jdbc(
        url=jdbc_url(),
        table="hourly_water_level_agg",
        mode="append",
        properties=jdbc_props(),
    )

    write_log(
        spark,
        run_id,
        "write_hourly_aggregation",
        "INFO",
        "SUCCESS",
        f"Spark wrote {count_rows} hourly aggregation rows to PostgreSQL.",
        count_rows,
    )


def write_anomaly_batch(batch_df, batch_id):
    spark = batch_df.sparkSession
    run_id = f"spark_anomaly_batch_{batch_id}"

    if batch_df.rdd.isEmpty():
        return

    anomaly = (
        batch_df
        .withColumn(
            "anomaly_type",
            when((col("data_flags").isNotNull()) & (col("data_flags") != lit("0,0")), lit("DATA_FLAG_WARNING"))
            .when((col("sigma").isNotNull()) & (col("sigma") > lit(0.05)), lit("HIGH_SIGMA_WARNING"))
            .when(col("water_level_m") >= lit(1.204), lit("MAJOR_CURRENT_RISK"))
            .when(col("water_level_m") >= lit(0.825), lit("MODERATE_CURRENT_RISK"))
            .otherwise(lit(None))
        )
        .where(col("anomaly_type").isNotNull())
        .withColumn(
            "severity",
            when(col("water_level_m") >= lit(1.204), lit("FATAL")).otherwise(lit("WARNING"))
        )
        .withColumn("previous_water_level_m", lit(None).cast("double"))
        .withColumn("delta_m", lit(None).cast("double"))
        .withColumn("message", col("anomaly_type"))
        .select(
            col("station_id"),
            col("observation_time"),
            col("water_level_m"),
            col("previous_water_level_m"),
            col("delta_m"),
            col("anomaly_type"),
            col("severity"),
            col("message"),
            current_timestamp().alias("created_at"),
        )
    )

    count_rows = anomaly.count()
    if count_rows == 0:
        print(f"[Spark] write_anomaly_batch: no anomalies detected")
        return

    anomaly.write.jdbc(
        url=jdbc_url(),
        table="stream_anomaly_log",
        mode="append",
        properties=jdbc_props(),
    )

    write_log(
        spark,
        run_id,
        "write_anomaly_log",
        "WARNING",
        "SUCCESS",
        f"Spark wrote {count_rows} anomaly rows.",
        count_rows,
    )
    print(f"[Spark] write_anomaly_batch: {count_rows} anomalies detected")


def main():
    spark = (
        SparkSession.builder
        .appName("NOAA Rob Spark Structured Streaming")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")
    print("SparkSession started for NOAA Rob stream processing.", flush=True)

    kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    topic = os.getenv("KAFKA_TOPIC_RAW", "noaa_water_level_raw")
    print(f"Reading Kafka topic: {topic} from {kafka_bootstrap}", flush=True)

    schema = StructType([
        StructField("station_id", StringType(), True),
        StructField("station_name", StringType(), True),
        StructField("observation_time", StringType(), True),
        StructField("water_level_m", DoubleType(), True),
        StructField("sigma", DoubleType(), True),
        StructField("data_flags", StringType(), True),
        StructField("datum", StringType(), True),
        StructField("source_product", StringType(), True),
        StructField("ingested_at", StringType(), True),
    ])

    raw_kafka = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", kafka_bootstrap)
        .option("subscribe", topic)
        .option("startingOffsets", "latest")
        .load()
    )

    parsed = (
        raw_kafka
        .select(
            col("topic").alias("kafka_topic"),
            col("partition").alias("kafka_partition"),
            col("offset").alias("kafka_offset"),
            col("timestamp").alias("kafka_timestamp"),
            from_json(col("value").cast("string"), schema).alias("data")
        )
        .select(
            col("data.station_id").alias("station_id"),
            col("data.station_name").alias("station_name"),
            to_timestamp(col("data.observation_time")).alias("observation_time"),
            col("data.water_level_m").cast("double").alias("water_level_m"),
            col("data.sigma").cast("double").alias("sigma"),
            col("data.data_flags").alias("data_flags"),
            col("data.datum").alias("datum"),
            col("data.source_product").alias("source_product"),
            col("kafka_topic"),
            col("kafka_partition"),
            col("kafka_offset"),
        )
        .where(col("station_id").isNotNull())
        .where(col("observation_time").isNotNull())
        .where(col("water_level_m").isNotNull())
    )

    checkpoint_base = os.getenv("SPARK_CHECKPOINT_DIR", "/tmp/noaa_spark_checkpoints")

    raw_query = (
        parsed.writeStream
        .foreachBatch(write_raw_batch)
        .outputMode("append")
        .option("checkpointLocation", f"{checkpoint_base}/raw")
        .start()
    )

    hourly_query = (
        parsed.writeStream
        .foreachBatch(write_hourly_batch)
        .outputMode("append")
        .option("checkpointLocation", f"{checkpoint_base}/hourly")
        .start()
    )

    anomaly_query = (
        parsed.writeStream
        .foreachBatch(write_anomaly_batch)
        .outputMode("append")
        .option("checkpointLocation", f"{checkpoint_base}/anomaly")
        .start()
    )

    write_log(
        spark,
        "spark_streaming_startup",
        "start_spark_streaming",
        "INFO",
        "RUNNING",
        f"Spark Structured Streaming started. Kafka topic: {topic}",
        0,
    )

    print("Spark Structured Streaming queries started. Waiting for Kafka messages...", flush=True)
    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
