from fastapi import FastAPI, Query
import joblib
import os
import pandas as pd
from pydantic import BaseModel
import logging

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model = joblib.load(os.path.join("models", "car_price_model.pkl"))

class CarFeatures(BaseModel):
    year: int
    mileage: int

@app.get("/healthz")
def health_check():
    logger.info("Health check endpoint called")
    return {"status": "ok"}

@app.post("/predict")
def predict(data: CarFeatures):
    input_df = pd.DataFrame([data.dict()])
    prediction = model.predict(input_df)[0]
    logger.info(f"Received prediction request: {data}")
    logger.info(f"Prediction result: {prediction}")
    return {"predicted_price": prediction}