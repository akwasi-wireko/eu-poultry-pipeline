"""A skeleton pipeline: three tiny tasks wired together by a flow for EU Poultry Prices."""

from prefect import flow, task
from prefect.runtime import task_run


@task(retries=2, retry_delay_seconds=3)
def fetch_poultry_prices(begin_date: str) -> list[dict]:
    """Simulate fetching weekly EU poultry prices from the DG AGRI API."""
    print(f"Fetching EU poultry prices from DG AGRI API starting {begin_date}...")
    if task_run.run_count == 1:
        raise ConnectionError("DG AGRI API didn't answer on the first try. Prefect will retry.")

    # Simulated raw JSON payload matching the EU poultry schema
    return [
        {
            "memberStateCode": "FR",
            "memberStateName": "France",
            "beginDate": "02/11/2026",
            "endDate": "08/11/2026",
            "weekNumber": 45,
            "productCode": "CHICKEN",
            "productName": "Whole chicken",
            "price": 265.40,
            "unit": "EUR/100kg",
        },
        {
            "memberStateCode": "PL",
            "memberStateName": "Poland",
            "beginDate": "02/11/2026",
            "endDate": "08/11/2026",
            "weekNumber": 45,
            "productCode": "CHICKEN",
            "productName": "Whole chicken",
            "price": 218.90,
            "unit": "EUR/100kg",
        },
    ]


@task
def validate_poultry_prices(raw_records: list[dict]) -> list[dict]:
    """Simulate validating the data contract (price > 0 and < 2000, valid week, deduplicated)."""
    print(f"Checking data contract rules on {len(raw_records)} raw poultry records...")
    valid_records = [
        record
        for record in raw_records
        if 0 < record["price"] < 2000 and 1 <= record["weekNumber"] <= 53
    ]
    print(f"Validated {len(valid_records)} records ready for Silver and Gold layers.")
    return valid_records


@task
def save_medallion_layers(raw_records: list[dict], valid_records: list[dict]) -> None:
    """Simulate saving raw JSON to Bronze, typed rows to Silver, and ML features to Gold."""
    print(f"Bronze: Saved {len(raw_records)} raw API records with ingestion timestamp.")
    print(f"Silver: Upserted {len(valid_records)} clean rows by (member_state_code, product_code, begin_date).")
    print("Gold: Computed weekly forecasting lags and rolling averages for ML.")


@flow(log_prints=True)
def hello_eu_poultry_pipeline(begin_date: str = "01/11/2026") -> list[dict]:
    """Run fetch, validate, and save tasks in order for the EU Poultry Prices pipeline."""
    print(f"Starting EU Poultry Prices pipeline (window start: {begin_date}).")
    raw_prices = fetch_poultry_prices(begin_date)
    clean_prices = validate_poultry_prices(raw_prices)
    save_medallion_layers(raw_prices, clean_prices)
    return clean_prices


if __name__ == "__main__":
    hello_eu_poultry_pipeline()