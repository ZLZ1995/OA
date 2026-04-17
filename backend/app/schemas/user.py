from pydantic import BaseModel, Field


class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    real_name: str = Field(min_length=1, max_length=64)
    email: str | None = None
    phone: str | None = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)
    role_codes: list[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    real_name: str | None = Field(default=None, min_length=1, max_length=64)
    email: str | None = None
    phone: str | None = None
    is_active: bool | None = None


class UserRoleBindRequest(BaseModel):
    role_codes: list[str] = Field(default_factory=list)


class UserResponse(BaseModel):
    id: int
    username: str
    real_name: str
    email: str | None
    phone: str | None
    is_active: bool
    roles: list[str]


class UserListResponse(BaseModel):
    items: list[UserResponse]
