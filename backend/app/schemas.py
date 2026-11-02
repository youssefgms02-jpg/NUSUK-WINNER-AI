from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

class KeyCreate(BaseModel):
    code: str = Field(min_length=1, max_length=240)
    category: str = "عام"
    source_name: str = "يدوي"
    source_url: str = ""
    notes: str = ""

class KeyOut(BaseModel):
    id: int
    code: str
    category: str
    source_name: str
    source_url: str
    status: str
    reviewed: bool
    notes: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ReviewUpdate(BaseModel):
    reviewed: bool

class SourceCreate(BaseModel):
    name: str
    feed_url: HttpUrl
