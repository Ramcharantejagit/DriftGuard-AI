from pydantic import BaseModel
from typing import Optional

class ExplainRequest(BaseModel):
    finding_id: str

class Finding(BaseModel):
    id: str
    type: str
    severity: str
    title: str
    message: str
    file: str
    line: int = 1
    suggestion: str = ""
    fingerprint: Optional[str] = None
