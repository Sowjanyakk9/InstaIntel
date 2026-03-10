from pydantic import BaseModel


class JobResponse(BaseModel):

    id: int
    dataset_id: int
    stage: str
    status: str
    progress: int