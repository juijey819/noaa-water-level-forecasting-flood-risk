import pandas as pd
from src.utils.db import read_sql
from src.models.predict_model import predict_from_hourly_history, save_prediction_result
from src.utils.logger import write_pipeline_log

if __name__ == "__main__":
    station_id = "8638610"
    query = """
        SELECT station_id,
               hour_timestamp AS timestamp,
               hourly_last_water_level_m AS water_level_m
        FROM hourly_water_level_agg
        WHERE station_id = %(station_id)s
        ORDER BY hour_timestamp
    """
    hourly = read_sql(query, params={"station_id": station_id})
    if len(hourly) < 200:
        raise RuntimeError(f"Not enough hourly aggregation rows for prediction. Current rows: {len(hourly)}")

    hourly["timestamp"] = pd.to_datetime(hourly["timestamp"])
    hourly["water_level_m"] = pd.to_numeric(hourly["water_level_m"], errors="coerce")

    pred = predict_from_hourly_history(hourly)
    save_prediction_result(pred)

    write_pipeline_log(
        run_id="manual_prediction_from_hourly_agg",
        pipeline_name="stream_prediction",
        component="python_prediction",
        task_name="predict_from_spark_hourly_agg",
        severity=str(pred.iloc[0]["severity"]),
        status="SUCCESS",
        message=f"Prediction saved for target {pred.iloc[0]['target_time']}. Risk: {pred.iloc[0]['predicted_risk_level']}",
        records_processed=1,
    )

    print(pred.to_string(index=False))
