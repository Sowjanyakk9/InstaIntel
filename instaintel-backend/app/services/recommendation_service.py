from sqlalchemy.orm import Session
from app.models.recommendations import Recommendation


def generate_kpi_recommendations(metadata, insights):

    recs = []

    for kpi in metadata.metrics_json:

        recs.append({
            "recommendation_type": "kpi",
            "priority": 2,
            "title": f"Monitor KPI {kpi}",
            "description": f"Track {kpi} performance closely",
            "evidence_json": {"kpi": kpi}
        })

    return recs


def generate_driver_recommendations(insights):

    recs = []

    for d in insights.stats_json.get("drivers", []):

        recs.append({
            "recommendation_type": "driver",
            "priority": 3,
            "title": f"Optimize {d['driver_column']}",
            "description": f"{d['driver_column']} strongly influences {d['target_metric']}",
            "evidence_json": d
        })

    return recs


def generate_forecast_recommendations(predictions):

    recs = []

    if predictions.risk_score > 60:

        recs.append({
            "recommendation_type": "risk",
            "priority": 4,
            "title": "Mitigate forecast risk",
            "description": "Forecast uncertainty indicates risk",
            "evidence_json": {"risk_score": predictions.risk_score}
        })

    return recs


def generate_domain_recommendations(domain, insights, predictions):

    recs = []

    if domain == "sales":

        recs.append({
            "recommendation_type": "domain",
            "priority": 3,
            "title": "Adjust pricing strategy",
            "description": "Sales performance suggests pricing optimization",
            "evidence_json": {"domain": domain}
        })

    return recs


def rank_recommendations(recommendations):

    return sorted(
        recommendations,
        key=lambda r: r["priority"],
        reverse=True
    )


def save_recommendations_to_db(db: Session, dataset_id, recs):

    records = []

    for r in recs:

        record = Recommendation(dataset_id=dataset_id, **r)

        db.add(record)
        records.append(record)

    db.commit()

    return records