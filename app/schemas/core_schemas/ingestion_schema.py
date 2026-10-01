from pydantic import BaseModel, Field
from typing import Optional

class IngestDirectoryRequest(BaseModel):
    directory_path: Optional[str] = Field(default="data/documents/", description="Directory to ingest from")
