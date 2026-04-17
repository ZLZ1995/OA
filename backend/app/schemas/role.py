from pydantic import BaseModel


class RoleOut(BaseModel):
    id: int
    code: str
    name: str
    description: str
