from pydantic import BaseModel, EmailStr


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminPublicProfile(BaseModel):
    id: str
    full_name: str | None = None
    email: str
    role: str = "admin"
