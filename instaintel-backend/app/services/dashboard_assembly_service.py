from __future__ import annotations

from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session

from app.models.alerts import Alert
from app.models.charts import Chart
from app.models.dashboards import Dashboard, DashboardWidget
from app.models.insights import Insight
from app.models.metadata import DatasetMetadata
from app.models.predictions import Prediction
from app.models.recommendations import Recommendation


def _extract_primary_kpi_names(primary_kpis_json: List[Any]) -> List[str]:
    names: List[str] = []

    for item in primary_kpis_json or []:
        if isinstance(item, dict):
            metric = item.get("metric")
            if metric:
                names.append(metric)
        elif isinstance(item, str):
            names.append(item)

    return names


def _metric_stats_map(insight: Insight | None) -> Dict[str, Dict[str, Any]]:
    if not insight or not insight.stats_json:
        return {}

    metrics = insight.stats_json.get("metrics", []) or []
    result: Dict[str, Dict[str, Any]] = {}

    for item in metrics:
        metric_name = item.get("metric")
        if metric_name:
            result[metric_name] = item

    return result


def _trend_map(insight: Insight | None) -> Dict[str, Dict[str, Any]]:
    if not insight or not insight.stats_json:
        return {}

    trends = insight.stats_json.get("trends", []) or []
    result: Dict[str, Dict[str, Any]] = {}

    for item in trends:
        metric_name = item.get("metric")
        if metric_name:
            result[metric_name] = item

    return result


def _forecast_summary(prediction: Prediction | None) -> Dict[str, Any]:
    if not prediction or not prediction.forecast_json:
        return {}

    forecast_json = prediction.forecast_json
    forecast_points = forecast_json.get("forecast_points", []) or []

    if not forecast_points:
        return {
            "prediction_type": forecast_json.get("prediction_type"),
            "target_metric": forecast_json.get("target_metric"),
            "next_predicted_value": None,
            "forecast_horizon": 0,
            "uncertainty_span_avg": None,
        }

    first_point = forecast_points[0]
    spreads: List[float] = []
    for point in forecast_points:
        lower = point.get("lower_bound")
        upper = point.get("upper_bound")
        if lower is not None and upper is not None:
            spreads.append(float(upper) - float(lower))

    uncertainty_span_avg = sum(spreads) / len(spreads) if spreads else None

    return {
        "prediction_type": forecast_json.get("prediction_type"),
        "target_metric": forecast_json.get("target_metric"),
        "next_predicted_value": first_point.get("predicted_value"),
        "forecast_horizon": len(forecast_points),
        "uncertainty_span_avg": uncertainty_span_avg,
    }


def _top_kpi_cards(
    metadata: DatasetMetadata | None,
    insight: Insight | None,
    prediction: Prediction | None,
) -> List[Dict[str, Any]]:
    if metadata is None:
        return []

    primary_kpis = _extract_primary_kpi_names(metadata.primary_kpis_json or [])
    stats_map = _metric_stats_map(insight)
    trends = _trend_map(insight)
    forecast = _forecast_summary(prediction)

    cards: List[Dict[str, Any]] = []

    for kpi in primary_kpis[:4]:
        stats = stats_map.get(kpi, {})
        trend = trends.get(kpi, {})

        payload: Dict[str, Any] = {
            "current_mean": stats.get("mean"),
            "current_median": stats.get("median"),
            "min": stats.get("min"),
            "max": stats.get("max"),
            "variance": stats.get("variance"),
            "trend_direction": trend.get("trend_direction"),
            "growth_rate": trend.get("growth_rate"),
        }

        subtitle = None
        if forecast.get("target_metric") == kpi and forecast.get("next_predicted_value") is not None:
            payload["next_predicted_value"] = forecast.get("next_predicted_value")
            payload["forecast_horizon"] = forecast.get("forecast_horizon")
            subtitle = "Includes forecast preview"

        cards.append(
            {
                "widget_type": "kpi_card",
                "config_json": {
                    "title": kpi,
                    "subtitle": subtitle,
                    "kpi_name": kpi,
                    "source_type": "metadata+insights+predictions",
                    "payload": payload,
                },
            }
        )

    # Fallback to metrics if no primary_kpis were stored
    if not cards:
        for metric_name, stats in list(stats_map.items())[:4]:
            cards.append(
                {
                    "widget_type": "kpi_card",
                    "config_json": {
                        "title": metric_name,
                        "subtitle": None,
                        "kpi_name": metric_name,
                        "source_type": "insights",
                        "payload": {
                            "current_mean": stats.get("mean"),
                            "current_median": stats.get("median"),
                            "min": stats.get("min"),
                            "max": stats.get("max"),
                            "variance": stats.get("variance"),
                        },
                    },
                }
            )

    return cards


def _select_chart_widgets(charts: List[Chart]) -> List[Dict[str, Any]]:
    chart_priority = {
        "line": 5,
        "bar": 4,
        "scatter": 3,
        "heatmap": 2,
        "histogram": 1,
    }

    ordered = sorted(
        charts,
        key=lambda chart: chart_priority.get(chart.chart_type, 0),
        reverse=True,
    )

    selected = ordered[:6]
    widgets: List[Dict[str, Any]] = []

    for chart in selected:
        widgets.append(
            {
                "widget_type": "chart",
                "config_json": {
                    "title": chart.chart_config_json.get("title", f"{chart.chart_type.title()} chart"),
                    "subtitle": None,
                    "chart_id": chart.id,
                    "source_type": "charts",
                    "payload": {
                        "chart_type": chart.chart_type,
                        "x_column": chart.x_column,
                        "y_column": chart.y_column,
                        "chart_config_json": chart.chart_config_json,
                    },
                },
            }
        )

    return widgets


def _build_summary_widget(insight: Insight | None) -> Dict[str, Any] | None:
    if not insight:
        return None

    ranked_insights = insight.stats_json.get("ranked_insights_json", []) if insight.stats_json else []
    top_ranked = ranked_insights[:5]

    return {
        "widget_type": "text_block",
        "config_json": {
            "title": "Summary",
            "subtitle": "Top findings",
            "source_type": "insights",
            "payload": {
                "summary_text": insight.summary_text,
                "ranked_insights_json": top_ranked,
            },
        },
    }


def _build_alert_widget(alerts: List[Alert]) -> Dict[str, Any] | None:
    if not alerts:
        return None

    top_alerts = alerts[:10]
    return {
        "widget_type": "alert_list",
        "config_json": {
            "title": "Alerts",
            "subtitle": "Highest priority alerts",
            "source_type": "alerts",
            "source_ids": [alert.id for alert in top_alerts],
            "payload": {
                "items": [
                    {
                        "id": alert.id,
                        "alert_type": alert.alert_type,
                        "severity": alert.severity,
                        "title": alert.title,
                        "description": alert.description,
                        "recommended_action": alert.recommended_action,
                        "evidence_json": alert.evidence_json,
                    }
                    for alert in top_alerts
                ]
            },
        },
    }


def _build_recommendation_widget(recommendations: List[Recommendation]) -> Dict[str, Any] | None:
    if not recommendations:
        return None

    top_recommendations = recommendations[:10]
    return {
        "widget_type": "recommendation_list",
        "config_json": {
            "title": "Recommendations",
            "subtitle": "Suggested next actions",
            "source_type": "recommendations",
            "source_ids": [rec.id for rec in top_recommendations],
            "payload": {
                "items": [
                    {
                        "id": rec.id,
                        "recommendation_type": rec.recommendation_type,
                        "priority": rec.priority,
                        "title": rec.title,
                        "description": rec.description,
                        "evidence_json": rec.evidence_json,
                    }
                    for rec in top_recommendations
                ]
            },
        },
    }


def _default_filters(metadata: DatasetMetadata | None) -> Dict[str, Any]:
    if metadata is None:
        return {}

    return {
        "time_columns": metadata.time_columns_json or [],
        "dimensions": metadata.dimensions_json or [],
        "metrics": metadata.metrics_json or [],
        "domain": metadata.domain_detected,
    }


def _place_widgets(
    top_cards: List[Dict[str, Any]],
    chart_widgets: List[Dict[str, Any]],
    summary_widget: Dict[str, Any] | None,
    alert_widget: Dict[str, Any] | None,
    recommendation_widget: Dict[str, Any] | None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    widgets: List[Dict[str, Any]] = []

    # Row 0: KPI cards, 4-column grid
    for idx, widget in enumerate(top_cards):
        widgets.append(
            {
                **widget,
                "position": {
                    "row": 0,
                    "col": idx * 3,
                    "width": 3,
                    "height": 2,
                },
            }
        )

    current_row = 2

    # Row 2+: summary block on left, alerts on right
    if summary_widget:
        widgets.append(
            {
                **summary_widget,
                "position": {
                    "row": current_row,
                    "col": 0,
                    "width": 8,
                    "height": 3,
                },
            }
        )

    if alert_widget:
        widgets.append(
            {
                **alert_widget,
                "position": {
                    "row": current_row,
                    "col": 8,
                    "width": 4,
                    "height": 3,
                },
            }
        )

    if summary_widget or alert_widget:
        current_row += 3

    # Middle rows: charts in 2-column layout
    chart_row = current_row
    chart_col_positions = [0, 6]
    for idx, widget in enumerate(chart_widgets):
        widgets.append(
            {
                **widget,
                "position": {
                    "row": chart_row,
                    "col": chart_col_positions[idx % 2],
                    "width": 6,
                    "height": 4,
                },
            }
        )
        if idx % 2 == 1:
            chart_row += 4

    if len(chart_widgets) % 2 == 1:
        chart_row += 4

    # Bottom row: recommendations
    if recommendation_widget:
        widgets.append(
            {
                **recommendation_widget,
                "position": {
                    "row": chart_row,
                    "col": 0,
                    "width": 12,
                    "height": 3,
                },
            }
        )
        chart_row += 3

    layout_json = {
        "grid": {
            "columns": 12,
            "row_height": 120,
            "gap": 16,
        },
        "sections": [
            {"name": "top_kpis", "row_start": 0},
            {"name": "summary_alerts", "row_start": 2},
            {"name": "charts", "row_start": current_row},
            {"name": "recommendations", "row_start": chart_row - 3 if recommendation_widget else chart_row},
        ],
        "default_filters": {},
    }

    return layout_json, widgets


def build_dashboard_definition(dataset_id: int, db: Session) -> Dict[str, Any]:
    metadata = db.query(DatasetMetadata).filter(DatasetMetadata.dataset_id == dataset_id).first()
    insight = db.query(Insight).filter(Insight.dataset_id == dataset_id).first()
    prediction = db.query(Prediction).filter(Prediction.dataset_id == dataset_id).first()

    alerts = (
        db.query(Alert)
        .filter(Alert.dataset_id == dataset_id)
        .order_by(Alert.created_at.desc())
        .all()
    )

    recommendations = (
        db.query(Recommendation)
        .filter(Recommendation.dataset_id == dataset_id)
        .order_by(Recommendation.priority.desc(), Recommendation.created_at.desc())
        .all()
    )

    charts = (
        db.query(Chart)
        .filter(Chart.dataset_id == dataset_id)
        .order_by(Chart.created_at.asc())
        .all()
    )

    domain = metadata.domain_detected if metadata else "generic"
    dataset_title = f"InstaIntel Dashboard - Dataset {dataset_id}"
    if domain and domain != "generic":
        dataset_title = f"InstaIntel Dashboard - {domain.title()} Dataset {dataset_id}"

    top_cards = _top_kpi_cards(metadata, insight, prediction)
    chart_widgets = _select_chart_widgets(charts)
    summary_widget = _build_summary_widget(insight)
    alert_widget = _build_alert_widget(alerts)
    recommendation_widget = _build_recommendation_widget(recommendations)

    layout_json, widgets = _place_widgets(
        top_cards=top_cards,
        chart_widgets=chart_widgets,
        summary_widget=summary_widget,
        alert_widget=alert_widget,
        recommendation_widget=recommendation_widget,
    )

    layout_json["default_filters"] = _default_filters(metadata)

    return {
        "dataset_id": dataset_id,
        "title": dataset_title,
        "layout_json": layout_json,
        "widgets": widgets,
    }


def save_dashboard_to_db(db: Session, dataset_id: int, dashboard_definition: Dict[str, Any]) -> Dashboard:
    existing_dashboard = db.query(Dashboard).filter(Dashboard.dataset_id == dataset_id).first()

    if existing_dashboard:
        db.query(DashboardWidget).filter(DashboardWidget.dashboard_id == existing_dashboard.id).delete()
        db.commit()

        existing_dashboard.title = dashboard_definition["title"]
        existing_dashboard.layout_json = dashboard_definition["layout_json"]
        db.commit()
        db.refresh(existing_dashboard)
        dashboard = existing_dashboard
    else:
        dashboard = Dashboard(
            dataset_id=dataset_id,
            title=dashboard_definition["title"],
            layout_json=dashboard_definition["layout_json"],
        )
        db.add(dashboard)
        db.commit()
        db.refresh(dashboard)

    for widget in dashboard_definition["widgets"]:
        db.add(
            DashboardWidget(
                dashboard_id=dashboard.id,
                widget_type=widget["widget_type"],
                position=widget["position"],
                config_json=widget["config_json"],
            )
        )

    db.commit()
    db.refresh(dashboard)
    return dashboard