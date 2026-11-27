"""Settings in one place. Values come from the environment or .env, with safe defaults."""

import os

from dotenv import load_dotenv

load_dotenv()  # Reads .env from the folder you run the command in, if it exists.

DATABASE = os.getenv("DATABASE_URL") or "data/pipeline.sqlite3"
BRONZE_DIR = os.getenv("BRONZE_DIR") or "data/bronze"

# EU Agri-food Poultry API endpoint and request timeout.
BASE_URL = (
    os.getenv("POULTRY_API_URL") or "https://api.tech.ec.europa.eu/agrifood/api/poultry/prices"
)
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT") or 30.0)

# Default poultry filters to collect. Override or extend as needed.
MEMBER_STATE_CODES = None  # EU ISO2 country codes (e.g., PT, ES, FR, DE)
PRODUCTS = None  # Allowed: "Broiler", "Breast", "Legs"
PRICE_TYPES = [
    "Selling price"
]  # Allowed: "Selling price", "Retail buying prices", "Non-retail buying prices", "All"

FIRST_LOAD_DAYS = 365  # Weekly data: 1 year of history on the very first run.
OVERLAP_DAYS = 21  # Re-read the last 3 weeks on later runs to catch revised weekly figures.
