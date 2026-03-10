from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models.insights import Insight


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _normalize_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    return pd.to_numeric(series, errors="coerce")


def _classify_distribution_shape(series: pd.Series) -> str:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty or len(clean) < 3:
        return "unknown"

    skewness = _safe_float(clean.skew(), 0.0)
    nunique_ratio = clean.nunique() / max(len(clean), 1)

    if nunique_ratio < 0.05:
        return "multimodal"
    if skewness > 1.0:
        return "skewed_right"
    if skewness < -1.0:
        return "skewed_left"
    return "normal"


def _correlation_strength(value: float) -> str:
    abs_value = abs(value)
    if abs_value >= 0.7:
        return "strong"
    if abs_value >= 0.4:
        return "moderate"
    return "weak"


def _parse_time_column(df: pd.DataFrame, time_columns: Sequence[str]) -> Optional[str]:
    for col in time_columns:
        if col not in df.columns:
            continue
        parsed = pd.to_datetime(df[col], errors="coerce")
        if parsed.notna().sum() >= 2:
            df[col] = parsed
            return col
    return None


def compute_summary_stats(df: pd.DataFrame, metrics: Sequence[str]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    for metric in metrics:
        if metric not in df.columns:
            continue

        series = pd.to_numeric(df[metric], errors="coerce").dropna()
        if series.empty:
            continue

        results.append(
            {
                "metric": metric,
                "mean": _safe_float(series.mean()),
                "median": _safe_float(series.median()),
                "min": _safe_float(series.min()),
                "max": _safe_float(series.max()),
                "variance": _safe_float(series.var(ddof=1), 0.0),
                "std_dev": _safe_float(series.std(ddof=1), 0.0),
                "distribution_shape": _classify_distribution_shape(series),
            }
        )

    return results


def compute_correlations(df: pd.DataFrame, metrics: Sequence[str]) -> List[Dict[str, Any]]:
    usable_metrics = [m for m in metrics if m in df.columns]
    results: List[Dict[str, Any]] = []

    for i, metric_x in enumerate(usable_metrics):
        for metric_y in usable_metrics[i + 1 :]:
            x = pd.to_numeric(df[metric_x], errors="coerce")
            y = pd.to_numeric(df[metric_y], errors="coerce")

            pair_df = pd.DataFrame({"x": x, "y": y}).dropna()
            if len(pair_df) < 3:
                continue

            pearson = _safe_float(pair_df["x"].corr(pair_df["y"], method="pearson"))
            spearman = _safe_float(pair_df["x"].corr(pair_df["y"], method="spearman"))
            strength = _correlation_strength(max(abs(pearson), abs(spearman)))

            results.append(
                {
                    "metric_x": metric_x,
                    "metric_y": metric_y,
                    "pearson": pearson,
                    "spearman": spearman,
                    "strength": strength,
                }
            )

    results.sort(
        key=lambda item: max(abs(item["pearson"]), abs(item["spearman"])),
        reverse=True,
    )
    return results


def compute_trends(
    df: pd.DataFrame,
    metrics: Sequence[str],
    time_columns: Sequence[str],
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    time_column = _parse_time_column(df.copy(), time_columns)

    if not time_column:
        return results

    working_df = df.copy()
    working_df[time_column] = pd.to_datetime(working_df[time_column], errors="coerce")
    working_df = working_df.dropna(subset=[time_column]).sort_values(time_column)

    for metric in metrics:
        if metric not in working_df.columns:
            continue

        temp = working_df[[time_column, metric]].copy()
        temp[metric] = pd.to_numeric(temp[metric], errors="coerce")
        temp = temp.dropna()
        if len(temp) < 3:
            continue

        grouped = temp.groupby(time_column, as_index=False)[metric].mean()
        if len(grouped) < 3:
            continue

        y = grouped[metric].astype(float).values
        x = np.arange(len(y), dtype=float)

        slope = np.polyfit(x, y, 1)[0]
        first = float(y[0]) if y[0] != 0 else 1.0
        last = float(y[-1])
        growth_rate = ((last - first) / abs(first)) * 100.0

        pct_changes = pd.Series(y).pct_change().replace([np.inf, -np.inf], np.nan).dropna()
        volatility = _safe_float(pct_changes.std(), 0.0)

        abs_growth = abs(growth_rate)
        if volatility > 0.4:
            trend_direction = "volatile"
        elif abs_growth < 3.0:
            trend_direction = "flat"
        elif slope > 0:
            trend_direction = "up"
        else:
            trend_direction = "down"

        seasonality_detected = False
        if len(y) >= 6:
            autocorr = pd.Series(y).autocorr(lag=max(1, min(3, len(y) // 3)))
            seasonality_detected = abs(_safe_float(autocorr, 0.0)) >= 0.5

        results.append(
            {
                "metric": metric,
                "time_column": time_column,
                "trend_direction": trend_direction,
                "growth_rate": _safe_float(growth_rate),
                "seasonality_detected": bool(seasonality_detected),
            }
        )

    return results


def detect_anomalies(
    df: pd.DataFrame,
    metrics: Sequence[str],
    time_columns: Sequence[str],
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    parsed_time_column = _parse_time_column(df.copy(), time_columns)

    for metric in metrics:
        if metric not in df.columns:
            continue

        series = pd.to_numeric(df[metric], errors="coerce")
        clean = series.dropna()
        if len(clean) < 3:
            continue

        mean = clean.mean()
        std = clean.std(ddof=1)
        if std == 0 or pd.isna(std):
            continue

        z_scores = ((clean - mean) / std).abs()
        anomaly_indexes = z_scores[z_scores >= 2.5].index.tolist()

        for idx in anomaly_indexes[:10]:
            value = _safe_float(series.loc[idx])
            direction = "spike" if value > mean else "drop"
            severity_score = min(100.0, abs((value - mean) / std) * 20.0)

            if parsed_time_column and parsed_time_column in df.columns:
                key_value = str(df.loc[idx, parsed_time_column])
            else:
                key_value = str(idx)

            results.append(
                {
                    "metric": metric,
                    "time_or_group_key": key_value,
                    "anomaly_type": direction if direction in {"spike", "drop"} else "outlier",
                    "severity_score": _safe_float(severity_score),
                }
            )

    results.sort(key=lambda item: item["severity_score"], reverse=True)
    return results


def compute_drivers(
    df: pd.DataFrame,
    metrics: Sequence[str],
    dimensions: Sequence[str],
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    usable_metrics = [m for m in metrics if m in df.columns]
    usable_dimensions = [d for d in dimensions if d in df.columns]

    # Metric-driven drivers via correlation
    for target_metric in usable_metrics:
        target_series = pd.to_numeric(df[target_metric], errors="coerce")

        for driver_metric in usable_metrics:
            if driver_metric == target_metric:
                continue

            driver_series = pd.to_numeric(df[driver_metric], errors="coerce")
            pair_df = pd.DataFrame({"target": target_series, "driver": driver_series}).dropna()
            if len(pair_df) < 3:
                continue

            corr_value = _safe_float(pair_df["target"].corr(pair_df["driver"], method="pearson"))
            if abs(corr_value) < 0.4:
                continue

            results.append(
                {
                    "target_metric": target_metric,
                    "driver_column": driver_metric,
                    "importance_score": round(abs(corr_value) * 100.0, 2),
                    "method": "correlation",
                }
            )

    # Dimension-driven drivers via between-group variance ratio
    for target_metric in usable_metrics:
        metric_series = pd.to_numeric(df[target_metric], errors="coerce")
        metric_df = pd.DataFrame({"metric": metric_series})

        total_variance = _safe_float(metric_df["metric"].var(ddof=1), 0.0)
        if total_variance <= 0:
            continue

        for dimension in usable_dimensions:
            temp = pd.DataFrame(
                {
                    "dimension": df[dimension].astype(str),
                    "metric": metric_series,
                }
            ).dropna()

            if temp.empty or temp["dimension"].nunique() < 2:
                continue

            grouped = temp.groupby("dimension")["metric"].mean()
            if grouped.empty:
                continue

            importance = _safe_float(grouped.var(ddof=1) / total_variance, 0.0) * 100.0
            if importance < 5.0:
                continue

            results.append(
                {
                    "target_metric": target_metric,
                    "driver_column": dimension,
                    "importance_score": round(min(100.0, importance), 2),
                    "method": "variance_explained",
                }
            )

    # Deduplicate by target+driver, keep highest importance
    deduped: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for item in results:
        key = (item["target_metric"], item["driver_column"])
        if key not in deduped or item["importance_score"] > deduped[key]["importance_score"]:
            deduped[key] = item

    final_results = list(deduped.values())
    final_results.sort(key=lambda item: item["importance_score"], reverse=True)
    return final_results[:25]


def rank_insights(
    all_findings: Dict[str, Any],
    primary_kpis: Sequence[Any],
    domain: str,
) -> List[Dict[str, Any]]:
    ranked: List[Dict[str, Any]] = []

    if primary_kpis and isinstance(primary_kpis[0], dict):
        primary_kpi_names = {item.get("metric") for item in primary_kpis if item.get("metric")}
    else:
        primary_kpi_names = set(primary_kpis)

    def kpi_relevance(metric_name: str) -> float:
        return 30.0 if metric_name in primary_kpi_names else 10.0

    # Anomalies
    for anomaly in all_findings.get("anomalies", []):
        metric = anomaly["metric"]
        score = min(100.0, 35.0 + kpi_relevance(metric) + anomaly["severity_score"] * 0.35)
        ranked.append(
            {
                "insight_type": "anomaly",
                "title": f"Anomaly detected in {metric}",
                "description": f"{metric} shows a {anomaly['anomaly_type']} at {anomaly['time_or_group_key']} with severity {round(anomaly['severity_score'], 2)}.",
                "priority_score": round(score, 2),
                "evidence_refs": [f"anomalies:{metric}:{anomaly['time_or_group_key']}"],
            }
        )

    # Trends
    for trend in all_findings.get("trends", []):
        metric = trend["metric"]
        growth = abs(_safe_float(trend["growth_rate"]))
        score = min(100.0, 20.0 + kpi_relevance(metric) + min(30.0, growth * 0.4))
        ranked.append(
            {
                "insight_type": "trend",
                "title": f"{metric} trend is {trend['trend_direction']}",
                "description": f"{metric} is trending {trend['trend_direction']} with growth rate {round(trend['growth_rate'], 2)}% over {trend['time_column']}.",
                "priority_score": round(score, 2),
                "evidence_refs": [f"trends:{metric}:{trend['time_column']}"],
            }
        )

    # Correlations
    for corr in all_findings.get("correlations", []):
        strongest = max(abs(corr["pearson"]), abs(corr["spearman"]))
        score = min(
            100.0,
            15.0 + kpi_relevance(corr["metric_x"]) + kpi_relevance(corr["metric_y"]) / 2.0 + strongest * 30.0,
        )
        ranked.append(
            {
                "insight_type": "correlation",
                "title": f"{corr['metric_x']} and {corr['metric_y']} are {corr['strength']}ly related",
                "description": f"{corr['metric_x']} and {corr['metric_y']} show Pearson {round(corr['pearson'], 2)} and Spearman {round(corr['spearman'], 2)} correlation.",
                "priority_score": round(score, 2),
                "evidence_refs": [f"correlations:{corr['metric_x']}:{corr['metric_y']}"],
            }
        )

    # Drivers
    for driver in all_findings.get("drivers", []):
        metric = driver["target_metric"]
        score = min(100.0, 18.0 + kpi_relevance(metric) + driver["importance_score"] * 0.35)
        ranked.append(
            {
                "insight_type": "driver",
                "title": f"{driver['driver_column']} is a driver of {metric}",
                "description": f"{driver['driver_column']} influences {metric} with importance score {round(driver['importance_score'], 2)} using {driver['method']}.",
                "priority_score": round(score, 2),
                "evidence_refs": [f"drivers:{metric}:{driver['driver_column']}"],
            }
        )

    # Summary-level metric insights
    for metric_stats in all_findings.get("metrics", []):
        metric = metric_stats["metric"]
        variance = _safe_float(metric_stats["variance"])
        score = min(100.0, 10.0 + kpi_relevance(metric) + min(20.0, variance * 0.01))
        ranked.append(
            {
                "insight_type": "summary",
                "title": f"{metric} summary profile",
                "description": f"{metric} ranges from {round(metric_stats['min'], 2)} to {round(metric_stats['max'], 2)} with mean {round(metric_stats['mean'], 2)}.",
                "priority_score": round(score, 2),
                "evidence_refs": [f"metrics:{metric}"],
            }
        )

    # Domain boost for classic sales/finance keywords
    if domain in {"sales", "finance", "marketing", "hr", "logistics"}:
        for item in ranked:
            if any(token in item["title"].lower() for token in ["revenue", "profit", "cost", "sales"]):
                item["priority_score"] = round(min(100.0, item["priority_score"] + 5.0), 2)

    ranked.sort(key=lambda item: item["priority_score"], reverse=True)
    return ranked[:25]


def build_summary_text(ranked_insights: Sequence[Dict[str, Any]]) -> str:
    if not ranked_insights:
        return "No significant insights were generated from the dataset."

    top_items = ranked_insights[:3]
    sentences = [item["description"] for item in top_items]
    return " ".join(sentences)


def save_insights_to_db(
    db: Session,
    dataset_id: int,
    summary_text: str,
    stats_json: Dict[str, Any],
) -> Insight:
    existing = db.query(Insight).filter(Insight.dataset_id == dataset_id).first()
    if existing:
        existing.summary_text = summary_text
        existing.stats_json = stats_json
        db.commit()
        db.refresh(existing)
        return existing

    insight = Insight(
        dataset_id=dataset_id,
        summary_text=summary_text,
        stats_json=stats_json,
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return insight


def build_insights_output(
    df: pd.DataFrame,
    metrics: Sequence[str],
    dimensions: Sequence[str],
    time_columns: Sequence[str],
    primary_kpis: Sequence[Any],
    domain: str,
) -> Dict[str, Any]:
    summary_stats = compute_summary_stats(df, metrics)
    correlations = compute_correlations(df, metrics)
    trends = compute_trends(df, metrics, time_columns)
    anomalies = detect_anomalies(df, metrics, time_columns)
    drivers = compute_drivers(df, metrics, dimensions)

    stats_json = {
        "metrics": summary_stats,
        "correlations": correlations,
        "trends": trends,
        "anomalies": anomalies,
        "drivers": drivers,
    }

    ranked_insights_json = rank_insights(stats_json, primary_kpis, domain)
    summary_text = build_summary_text(ranked_insights_json)

    return {
        "summary_text": summary_text,
        "stats_json": stats_json,
        "ranked_insights_json": ranked_insights_json,
    }