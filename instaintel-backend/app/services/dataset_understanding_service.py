import pandas as pd
from sqlalchemy.orm import Session
from app.models.metadata import DatasetMetadata


METRIC_KEYWORDS = [
    "revenue", "sales", "profit", "cost",
    "amount", "price", "quantity", "units",
    "score", "value"
]

TIME_KEYWORDS = [
    "date", "time", "month", "year", "timestamp"
]

ID_KEYWORDS = [
    "id", "uuid", "key"
]

TEXT_THRESHOLD = 50


def classify_columns(df: pd.DataFrame):

    columns_info = []

    metrics = []
    dimensions = []
    time_columns = []
    text_columns = []
    id_columns = []

    for column in df.columns:

        col_lower = column.lower()

        series = df[column]

        semantic_type = "unknown"

        if any(k in col_lower for k in TIME_KEYWORDS):
            semantic_type = "time"
            time_columns.append(column)

        elif any(k in col_lower for k in ID_KEYWORDS) and series.nunique() == len(series):
            semantic_type = "id"
            id_columns.append(column)

        elif pd.api.types.is_numeric_dtype(series):

            semantic_type = "metric"
            metrics.append(column)

        elif series.dtype == "object":

            avg_length = series.astype(str).str.len().mean()

            if avg_length > TEXT_THRESHOLD:
                semantic_type = "text"
                text_columns.append(column)
            else:
                semantic_type = "dimension"
                dimensions.append(column)

        columns_info.append({
            "column_name": column,
            "semantic_type": semantic_type,
            "detected_type": str(series.dtype),
            "confidence": 0.8
        })

    return {
        "columns_json": columns_info,
        "metrics": metrics,
        "dimensions": dimensions,
        "time_columns": time_columns,
        "text_columns": text_columns,
        "id_columns": id_columns
    }


def infer_domain(classified_columns):

    column_names = [c["column_name"].lower() for c in classified_columns]

    if any("revenue" in c or "sales" in c for c in column_names):
        return "sales"

    if any("cost" in c or "expense" in c for c in column_names):
        return "finance"

    if any("employee" in c or "salary" in c for c in column_names):
        return "hr"

    if any("shipment" in c or "warehouse" in c for c in column_names):
        return "logistics"

    if any("campaign" in c or "click" in c for c in column_names):
        return "marketing"

    return "generic"


def detect_kpis(df: pd.DataFrame, classified_columns, domain):

    metrics = classified_columns["metrics"]

    kpis = []

    for metric in metrics:

        variance = float(df[metric].var())

        score = 0

        if any(keyword in metric.lower() for keyword in METRIC_KEYWORDS):
            score += 40

        if variance > 0:
            score += 30

        score += 20

        kpis.append({
            "metric": metric,
            "score": score,
            "reasons": ["keyword_match", "variance"]
        })

    kpis = sorted(kpis, key=lambda x: x["score"], reverse=True)

    return kpis[:5]


def generate_analysis_plan(domain, kpis):

    insights = []
    predictions = []
    alerts = []
    recommendations = []

    if domain == "sales":

        insights = ["top_products", "top_regions", "revenue_trends"]
        predictions = ["revenue_forecast"]
        alerts = ["revenue_drop"]
        recommendations = ["increase_inventory"]

    elif domain == "finance":

        insights = ["cost_distribution", "margin_analysis"]
        predictions = ["cost_forecast"]
        alerts = ["cost_spike"]
        recommendations = ["reduce_expense"]

    else:

        insights = ["metric_summary"]
        predictions = []
        alerts = []
        recommendations = []

    return {
        "insights_to_generate": insights,
        "predictions_to_run": predictions,
        "alerts_to_monitor": alerts,
        "recommendations_to_generate": recommendations
    }


def save_metadata_to_db(
        db: Session,
        dataset_id,
        classification,
        domain,
        kpis,
        analysis_plan,
        row_count,
        column_count
):

    metadata = DatasetMetadata(
        dataset_id=dataset_id,
        columns_json=classification["columns_json"],
        metrics_json=classification["metrics"],
        dimensions_json=classification["dimensions"],
        time_columns_json=classification["time_columns"],
        text_columns_json=classification["text_columns"],
        id_columns_json=classification["id_columns"],
        domain_detected=domain,
        primary_kpis_json=kpis,
        analysis_plan_json=analysis_plan,
        row_count=row_count,
        column_count=column_count
    )

    db.add(metadata)
    db.commit()
    db.refresh(metadata)

    return metadata