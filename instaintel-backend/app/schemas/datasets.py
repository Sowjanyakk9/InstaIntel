from pydantic import BaseModel


class DatasetResponse(BaseModel):

    id: int
    file_path: str
    file_type: str
    status: str