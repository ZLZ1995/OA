from pydantic import BaseModel, Field, field_validator

PASSWORD_RULE_MESSAGE = "新密码必须为6-8位数字或英文，区分大小写"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordResetRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if not value.isalnum() or not value.isascii():
            raise ValueError(PASSWORD_RULE_MESSAGE)
        return value


class CurrentUserResponse(BaseModel):
    id: int
    username: str
    real_name: str
    roles: list[str]
