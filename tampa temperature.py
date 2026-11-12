import requests
import pandas as pd
import clickhouse_connect

ch = clickhouse_connect.get_client(
    host="localhost",
    port=8123,
    username="admin",
    password="Admin123"
)

api_url = "https://archive-api.open-meteo.com/v1/archive"

weather_params = {
    "latitude": 27.9506,
    "longitude": -82.4572,
    "start_date": "2026-10-01",
    "end_date": "2026-10-31",
    "hourly": "temperature_2m",
    "timezone": "America/New_York"
}

result = requests.get(api_url, params=weather_params, timeout=10)
result.raise_for_status()

weather_data = result.json()["hourly"]

print("weather information retrieved!")

# hourly records
hourly_df = pd.DataFrame(weather_data)

hourly_df["time"] = pd.to_datetime(hourly_df["time"])
hourly_df["date"] = hourly_df["time"].dt.date

hourly_df.rename(
    columns={"temperature_2m": "temperature"},
    inplace=True
)

hourly_df = hourly_df[["date", "time", "temperature"]]

print("\nHourly Weather Records:")
print(hourly_df.head())
print("Number of records:", hourly_df.shape[0])

# to generate daily temperature statistics
daily_df = (
    hourly_df.groupby("date")["temperature"]
    .agg(["min", "max"])
    .reset_index()
)

daily_df.rename(
    columns={
        "min": "minimum_temperature",
        "max": "maximum_temperature"
    },
    inplace=True
)

print("\nDaily Temperature Report:")
print(daily_df.head())
print("Number of daily records:", daily_df.shape[0])


ch.command("""
CREATE TABLE IF NOT EXISTS tampa_hourly_records
(
    date Date,
    time DateTime('America/New_York'),
    temperature Float64
)
ENGINE = MergeTree()
ORDER BY (date, time)
""")

ch.command("""
CREATE TABLE IF NOT EXISTS tampa_daily_report
(
    date Date,
    minimum_temperature Float64,
    maximum_temperature Float64
)
ENGINE = MergeTree()
ORDER BY date
""")

ch.command("TRUNCATE TABLE tampa_hourly_records")
ch.command("TRUNCATE TABLE tampa_daily_report")

ch.insert_df("tampa_hourly_records", hourly_df)
ch.insert_df("tampa_daily_report", daily_df)

print("\nHourly and daily data saved to ClickHouse.")
print("Weather data pipeline finished successfully!")