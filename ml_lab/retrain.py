"""
Retrain car_price_model_v2.pkl on the full production database.

Improvements over the original notebook:
- Pulls from the live PostgreSQL (122k records) instead of an 8k JSON dump
- Removes the 30-day recency filter — uses ALL historical data
- Fills NULL categorical features as "Unknown" instead of dropping rows
- Uses 200 estimators (was 100) for better forest stability
- Saves both v2 (full features) and v1-compat (year+mileage only)

Usage:
    # Run inside Docker on car-dev-net so it can reach postgres:5432
    docker run --rm \
      --network car-dev-net \
      -v $(pwd)/ml_api/models:/output \
      -v $(pwd)/ml_lab/retrain.py:/retrain.py \
      python:3.12 bash -c \
        "pip install -q psycopg2-binary pandas 'scikit-learn==1.3.0' 'numpy==1.26.4' joblib && python /retrain.py"
"""

import sys
import psycopg2
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LinearRegression
import joblib

DB_CONFIG = dict(
    host="postgres", port=5432, dbname="postgres",
    user="marketplace_user", password="marketplace_user",
)
OUTPUT_DIR = "/output"

def load_data():
    print("Connecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    query = """
        SELECT year, mileage, brand, model, gear_type, color,
               fuel_type, body_type, price
        FROM marketplace.cars
        WHERE year    IS NOT NULL
          AND mileage IS NOT NULL
          AND price   IS NOT NULL
          AND brand   IS NOT NULL
          AND model   IS NOT NULL
    """
    df = pd.read_sql(query, conn)
    conn.close()
    print(f"Loaded {len(df):,} rows")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ("price", "year", "mileage"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["price", "year", "mileage"])

    # Sanity ranges
    df = df[(df["year"]    >= 1990) & (df["year"]    <= 2026)]
    df = df[(df["mileage"] >= 0)    & (df["mileage"] <= 1_000_000)]
    df = df[(df["price"]   >= 200)  & (df["price"]   <= 300_000)]

    before = len(df)

    # Remove price outliers per brand/model group using residual from a fast
    # linear fit — catches e.g. currency-unformatted values like "12500000"
    X = df[["year", "mileage"]].values
    y = df["price"].values
    lr = LinearRegression().fit(X, y)
    residuals = np.abs(y - lr.predict(X))
    threshold = residuals.mean() + 3 * residuals.std()
    df = df[residuals < threshold]
    print(f"Removed {before - len(df):,} outliers → {len(df):,} remain")

    # Fill NULL categoricals so rows aren't dropped
    for col in ("gear_type", "color", "fuel_type", "body_type"):
        df[col] = df[col].fillna("Unknown")

    df = df.dropna()
    print(f"Final training set: {len(df):,} rows")
    return df


def train(df: pd.DataFrame):
    feature_cols = ["year", "mileage", "brand", "model",
                    "gear_type", "color", "fuel_type", "body_type"]
    num_cols = ["year", "mileage"]
    cat_cols = ["brand", "model", "gear_type", "color", "fuel_type", "body_type"]

    X = df[feature_cols]
    y = df["price"]

    preprocessor = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
    ], remainder="passthrough")

    # max_depth=20 caps tree size so the .pkl stays under ~100 MB on 120k records.
    # Without it a 200-tree forest on 120k rows grows to 1.4 GB.
    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("model", RandomForestRegressor(
            n_estimators=100, max_depth=20, random_state=42, n_jobs=-1,
        )),
    ])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print("Training v2 model (year+mileage+brand+model+gear+color+fuel+body)...")
    pipeline.fit(X_train, y_train)
    r2 = pipeline.score(X_test, y_test)
    print(f"  R² on test set: {r2:.4f}")

    # Rough RMSE
    preds = pipeline.predict(X_test)
    rmse = np.sqrt(np.mean((preds - y_test.values) ** 2))
    print(f"  RMSE: ${rmse:,.0f}")

    return pipeline


def train_simple(df: pd.DataFrame):
    """Train the year+mileage-only v1-compatible model."""
    X = df[["year", "mileage"]]
    y = df["price"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    m = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    print("Training v1 model (year+mileage only)...")
    m.fit(X_train, y_train)
    r2 = m.score(X_test, y_test)
    print(f"  R² on test set: {r2:.4f}")
    return m


def main():
    df_raw  = load_data()
    df      = clean(df_raw)

    model_v2  = train(df)
    model_v1  = train_simple(df)

    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    v2_path = f"{OUTPUT_DIR}/car_price_model_v2.pkl"
    v1_path = f"{OUTPUT_DIR}/car_price_model.pkl"
    joblib.dump(model_v2, v2_path)
    joblib.dump(model_v1, v1_path)
    print(f"Saved → {v2_path}")
    print(f"Saved → {v1_path}")


if __name__ == "__main__":
    main()
