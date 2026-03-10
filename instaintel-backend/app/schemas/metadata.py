from pydantic import BaseModel
from typing import List, Dict, Any


class MetadataResponse(BaseModel):

    dataset_id: int

    columns_json: List[Dict[str, Any]]

    metrics_json: List[str]

    dimensions_json: List[str]

    time_columns_json: List[str]

    text_columns_json: List[str]

    id_columns_json: List[str]

    domain_detected: str

    primary_kpis_json: List[Dict[str, Any]]

    analysis_plan_json: Dict[str, Any]

    row_count: int

    column_count: int