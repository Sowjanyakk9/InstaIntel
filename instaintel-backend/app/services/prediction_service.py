import os
import pickle
from datetime import datetime
from typing import Dict, Any, List

import numpy as np
import pandas as pd

from prophet import Prophet
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

from sqlalchemy.orm import Session

from app.models.predictions import Prediction
from app.models.ml_models import MLModel


MODEL_DIR = "models"


def select_prediction_method(metadata, insights):

    if metadata.time_columns_json:
        return "time_series"

    return "regression"


def run_time_series_forecast(df, kpi, time_column):

    temp = df[[time_column, kpi]].dropna()

    temp = temp.rename(columns={
        time_column: "ds",
        kpi: "y"
    })

    model = Prophet()

    model.fit(temp)

    future = model.make_future_dataframe(periods=10)

    forecast = model.predict(future)

    forecast_points = []

    for _, row in forecast.tail(10).iterrows():

        forecast_points.append({
            "period": str(row["ds"]),
            "predicted_value": float(row["yhat"]),
            "lower_bound": float(row["yhat_lower"]),
            "upper_bound": float(row["yhat_upper"])
        })

    uncertainty = compute_uncertainty(forecast_points)

    return {
        "prediction_type": "time_series",
        "target_metric": kpi,
        "time_column": time_column,
        "forecast_points": forecast_points,
        "uncertainty": uncertainty,
        "model": model
    }


def run_regression_prediction(df, kpi):

    df = df.dropna()

    features = df.drop(columns=[kpi]).select_dtypes(include=[np.number])

    target = df[kpi]

    model = LinearRegression()

    model.fit(features, target)

    predictions = model.predict(features)

    accuracy = r2_score(target, predictions)

    importance = []

    for col, coef in zip(features.columns, model.coef_):

        importance.append({
            "feature": col,
            "importance": float(abs(coef))
        })

    return {
        "prediction_type": "regression",
        "target_metric": kpi,
        "forecast_points": [],
        "feature_importance": importance,
        "model_quality": {
            "metric_name": "r2",
            "metric_value": float(accuracy)
        },
        "model": model
    }


def compute_uncertainty(forecast_points):

    if not forecast_points:
        return 0.0

    spreads = []

    for p in forecast_points:

        spread = p["upper_bound"] - p["lower_bound"]

        spreads.append(spread)

    return float(np.mean(spreads))


def compute_risk_score(volatility, anomalies, uncertainty, kpi_sensitivity):

    score = (
        volatility * 0.3 +
        anomalies * 0.3 +
        uncertainty * 0.2 +
        kpi_sensitivity * 0.2
    )

    return float(min(score, 100))


def save_prediction_results_to_db(
        db: Session,
        dataset_id,
        forecast_json,
        risk_score,
        risk_factors):

    prediction = Prediction(
        dataset_id=dataset_id,
        forecast_json=forecast_json,
        risk_score=risk_score,
        risk_factors_json=risk_factors
    )

    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    return prediction


def save_model_metadata_to_db(
        db: Session,
        dataset_id,
        model_type,
        model,
        accuracy):

    os.makedirs(MODEL_DIR, exist_ok=True)

    model_path = f"{MODEL_DIR}/model_{dataset_id}.pkl"

    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    record = MLModel(
        dataset_id=dataset_id,
        model_type=model_type,
        model_path=model_path,
        accuracy=accuracy,
        trained_at=datetime.utcnow()
    )

    db.add(record)
    db.commit()

    return record