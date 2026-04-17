from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    real_name: str = Field(min_length=1, max_length=64)
    email: str | None = None
    phone: str | None = None
    is_active: bool = True


class UserUpdate(BaseModel):
    real_name: str | None = Field(default=None, min_length=1, max_length=64)
    email: str | None = None
    phone: str | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    id: int
    username: str
    real_name: str
    email: str | None
    phone: str | None
    is_active: bool
    roles: list[str]


class RoleBindRequest(BaseModel):
    role_codes: list[str]
