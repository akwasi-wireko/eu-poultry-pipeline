# Pipeline plan

## Source
- What: weekly poultry prices across all EU Member States and product categories
- Where: European Commission (DG AGRI) Agri-food Data Portal API (https://api.tech.ec.europa.eu/agrifood/api/poultry/prices), no API key required
- Format: JSON, array of weekly price objects
- Terms: free for commercial and non-commercial use (European Commission open data)

## Record key
- One record = one poultry product in one Member State in one week
- Key: member_state_code + product_code + begin_date

## Data contract (what "valid" means)
- Required fields: memberStateCode, memberStateName, beginDate, endDate, weekNumber, productName, price, unit
- Types: string, string, date, date, integer, string, number, string
- Rules:
  1. price > 0 and < 2000 (EUR/100kg)
  2. begin_date <= end_date
  3. week_number between 1 and 53
  4. no duplicate member_state_code + product_code + begin_date

## Layers
- Bronze: the raw JSON response exactly as received, plus request URL and ingestion timestamp
- Silver: one cleaned, typed row per Member State, product, and week
- Gold: ML feature tables built in stages—(1) price forecasting lags & rolling stats, (2) anomaly scores, (3) country market clusters, and (4) EU average price spreads

## Cadence
- The source adds one week per week and occasionally revises recent weeks
- Backfill year-by-year from 2000, then run once a week re-reading the last 4 weeks each time

## What could go wrong
- API down or slow -> retry
- A field renamed or removed -> reject the batch, keep the Bronze copy
- A missed week or late country report -> the next weekly 4-week window catches up