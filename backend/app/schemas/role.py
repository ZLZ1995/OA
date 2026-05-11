from pydantic import BaseModel


class RoleResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str


class RoleListResponse(BaseModel):
    items: list[RoleResponse]
