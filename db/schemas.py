from datetime import datetime, date, time

from pydantic import BaseModel


class Permission(BaseModel):
    name: str
    description: str | None = None


class RolePermission(BaseModel):
    permission: str


class Role(BaseModel):
    id: int
    name: str
    description: str | None = None
    created: datetime
    permissions: list[RolePermission] = []

    class Config:
        orm_mode: True


class UserAccount(BaseModel):
    id: int
    username: str
    department: str | None = None
    role: str | None = None
    line_manager: str | None = None
    firstname: str
    middlename: str | None = None
    lastname: str
    gender: str
    email: str
    status: str
    identity: str
    identity_type: str
    enable_2_verification: bool
    created: datetime
    last_updated: datetime


class ActiveUser(BaseModel):
    username: str
    otp: int
    status: str
    expired_at: datetime
    attempts: int


class UserImage(BaseModel):
    id: int
    username: str
    image: str
    image_type: str
    created: datetime
    service_image_id: int | None = None


class UserToken(BaseModel):
    username: str
    token: str
    expired_at: datetime
    created: datetime


class FormReason(BaseModel):
    id: int
    name: str
    description: str | None = None
    productivity: str | None = None
    form_type: str


class FormDetail(BaseModel):
    id: int
    form: int
    from_time: time
    to_time: time
    from_date: date
    to_date: date


class Form(BaseModel):
    id: int
    form_status: str
    form_phase: str
    form_type: str
    reason: int
    form_reason: FormReason
    productivity: str
    department: str
    role: str
    created_user_obj: UserAccount
    assigned_user_obj: UserAccount
    description: str | None = None
    note: str | None = None
    created: datetime
    last_updated: datetime
    details: list[FormDetail] = []

    class Config:
        orm_mode: True


class Department(BaseModel):
    id: int
    name: str
    description: str | None = None
    created: datetime
    users: list[UserAccount] = []

    class Config:
        orm_mode: True
