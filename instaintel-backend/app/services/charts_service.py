from __future__ import annotations

from typing import Any, Dict, List, Sequence

from sqlalchemy.orm import Session

from app.models.charts import Chart


def generate_chart_specs(insights_output: Dict[str, Any]) -> List[Dict[str, Any]]:
    stats_json = insights_output["stats_json"]
    chart_specs: List[Dict[str, Any]] = []

    # Line charts for trends
    for trend in stats_json.get("trends", [])[:10]:
        chart_specs.append(
            {
                "chart_type": "line",
                "x_column": trend["time_column"],
                "y_column": trend["metric"],
                "chart_config_json": {
                    "title": f"{trend['metric']} over time",
                    "insight_type": "trend",
                    "trend_direction": trend["trend_direction"],
                },
            }
        )

    # Scatter plots for strong correlations
    for corr in stats_json.get("correlations", [])[:10]:
        if corr["strength"] == "strong":
            chart_specs.append(
                {
                    "chart_type": "scatter",
                    "x_column": corr["metric_x"],
                    "y_column": corr["metric_y"],
                    "chart_config_json": {
                        "title": f"{corr['metric_x']} vs {corr['metric_y']}",
                        "insight_type": "correlation",
                        "pearson": corr["pearson"],
                        "spearman": corr["spearman"],
                    },
                }
            )

    # Histogram for each metric
    for metric_stats in stats_json.get("metrics", [])[:10]:
        chart_specs.append(
            {
                "chart_type": "histogram",
                "x_column": metric_stats["metric"],
                "y_column": metric_stats["metric"],
                "chart_config_json": {
                    "title": f"{metric_stats['metric']} distribution",
                    "insight_type": "summary",
                    "distribution_shape": metric_stats["distribution_shape"],
                },
            }
        )

    # Bar charts for dimension-based drivers
    for driver in stats_json.get("drivers", [])[:10]:
        if driver["method"] == "variance_explained":
            chart_specs.append(
                {
                    "chart_type": "bar",
                    "x_column": driver["driver_column"],
                    "y_column": driver["target_metric"],
                    "chart_config_json": {
                        "title": f"{driver['driver_column']} impact on {driver['target_metric']}",
                        "insight_type": "driver",
                        "importance_score": driver["importance_score"],
                    },
                }
            )

    # Heatmap when there are several correlations
    if len(stats_json.get("correlations", [])) >= 2:
        chart_specs.append(
            {
                "chart_type": "heatmap",
                "x_column": "metrics",
                "y_column": "metrics",
                "chart_config_json": {
                    "title": "Metric correlation heatmap",
                    "insight_type": "correlation",
                    "pairs": [
                        {
                            "x": item["metric_x"],
                            "y": item["metric_y"],
                            "pearson": item["pearson"],
                            "spearman": item["spearman"],
                        }
                        for item in stats_json.get("correlations", [])[:25]
                    ],
                },
            }
        )

    # Deduplicate exact chart specs
    deduped: List[Dict[str, Any]] = []
    seen = set()
    for spec in chart_specs:
        key = (
            spec["chart_type"],
            spec["x_column"],
            spec["y_column"],
            str(spec["chart_config_json"].get("title", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(spec)

    return deduped[:25]


def save_chart_specs(
    db: Session,
    dataset_id: int,
    chart_specs: Sequence[Dict[str, Any]],
) -> List[Chart]:
    db.query(Chart).filter(Chart.dataset_id == dataset_id).delete()
    db.commit()

    created: List[Chart] = []
    for spec in chart_specs:
        chart = Chart(
            dataset_id=dataset_id,
            chart_type=spec["chart_type"],
            x_column=spec["x_column"],
            y_column=spec["y_column"],
            chart_config_json=spec["chart_config_json"],
        )
        db.add(chart)
        created.append(chart)

    db.commit()

    for chart in created:
        db.refresh(chart)

    return created