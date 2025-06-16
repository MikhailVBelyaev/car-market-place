import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib
import mlflow
import mlflow.pyfunc
import os

df = pd.read_csv("dbfs:/FileStore/cars_latest.csv")

X = df[["year", "mileage"]]
y = df["price"]

model = RandomForestRegressor()
model.fit(X, y)

model_path = "car_price_model.pkl"
joblib.dump(model, model_path)

class CarPriceModel(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        import joblib
        self.model = joblib.load(model_path)

    def predict(self, context, model_input):
        return self.model.predict(model_input)

with mlflow.start_run():
    mlflow.pyfunc.log_model(
        artifact_path="car_price_model",
        python_model=CarPriceModel(),
        input_example=pd.DataFrame({"year": [2010], "mileage": [150000]}),
        registered_model_name="car_price_model"
    )
