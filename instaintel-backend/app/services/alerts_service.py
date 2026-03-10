import numpy as np
from sqlalchemy.orm import Session
from app.models.alerts import Alert


def generate_kpi_alerts(df, metadata, insights):

    alerts = []

    for metric in metadata.metrics_json:

        if metric not in df.columns:
            continue

        std = df[metric].std()
        mean = df[metric].mean()

        latest = df[metric].iloc[-1]

        if abs(latest - mean) > 2 * std:

            alerts.append({
                "alert_type": "kpi_threshold",
                "severity": "high",
                "title": f"{metric} abnormal value",
                "description": f"{metric} shows extreme deviation",
                "evidence_json": {
                    "mean": float(mean),
                    "std": float(std),
                    "latest": float(latest)
                },
                "recommended_action": "Investigate metric deviation"
            })

    return alerts


def generate_forecast_alerts(predictions, metadata):

    alerts = []

    forecast = predictions.forecast_json

    if forecast["prediction_type"] == "time_series":

        for p in forecast["forecast_points"]:

            if p["predicted_value"] < p["lower_bound"]:

                alerts.append({
                    "alert_type": "forecast_deviation",
                    "severity": "medium",
                    "title": "Forecast below confidence bound",
                    "description": "Predicted KPI outside expected range",
                    "evidence_json": p,
                    "recommended_action": "Review forecast assumptions"
                })

    return alerts


def generate_risk_alerts(predictions, insights):

    alerts = []

    if predictions.risk_score > 70:

        alerts.append({
            "alert_type": "risk",
            "severity": "high",
            "title": "High system risk detected",
            "description": "Risk score indicates instability",
            "evidence_json": {
                "risk_score": predictions.risk_score
            },
            "recommended_action": "Investigate drivers of risk"
        })

    return alerts


def generate_domain_alerts(domain, df, metadata, insights):

    alerts = []

    if domain == "sales":

        if "revenue" in df.columns:

            growth = df["revenue"].pct_change().iloc[-1]

            if growth < -0.15:

                alerts.append({
                    "alert_type": "domain",
                    "severity": "high",
                    "title": "Revenue drop detected",
                    "description": "Significant revenue decline",
                    "evidence_json": {"growth": float(growth)},
                    "recommended_action": "Review pricing and promotions"
                })

    return alerts


def rank_alerts(alerts):

    severity_order = {"high": 3, "medium": 2, "low": 1}

    return sorted(
        alerts,
        key=lambda a: severity_order.get(a["severity"], 0),
        reverse=True
    )


def save_alerts_to_db(db: Session, dataset_id, alerts):

    saved = []

    for alert in alerts:

        record = Alert(dataset_id=dataset_id, **alert)

        db.add(record)
        saved.append(record)

    db.commit()

    return saved