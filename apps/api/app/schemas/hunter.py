from pydantic import BaseModel, Field

class HuntCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    query: str = Field(min_length=1)
    auto_hunt: bool = False

class HuntUpdate(BaseModel):
    name: str | None = None
    query: str | None = None
    auto_hunt: bool | None = None
    active: bool | None = None

class HuntParseRequest(BaseModel):
    query: str = Field(min_length=1)
