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
model_v2 = joblib.load(os.path.join("models", "car_price_model_v2.pkl"))

class CarFeatures(BaseModel):
    year: int
    mileage: int

class CarFeaturesV2(BaseModel):
    year: int
    mileage: int
    brand: str
    model: str
    gear_type: str
    color: str
    fuel_type: str
    body_type: str

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

@app.post("/predict2")
def predict_v2(data: CarFeaturesV2):
    input_df = pd.DataFrame([data.dict()])
    prediction = model_v2.predict(input_df)[0]
    logger.info(f"Received prediction request (v2): {data}")
    logger.info(f"Prediction result (v2): {prediction}")
    return {"predicted_price": prediction}