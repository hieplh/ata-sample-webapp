import enum
from datetime import datetime, date, time
from typing import Optional, List

from sqlalchemy import Integer, DateTime, Enum, ForeignKey, Time, Date, Boolean
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, relationship, mapped_column, Mapped


class Base(DeclarativeBase):
    def as_dict(self):
        """ convert model to json """
        result = {}
        for attr, value in self.__dict__.items():
            if not attr.startswith('_'):
                if isinstance(value, enum.Enum):
                    result[attr] = value.value
                elif isinstance(value, datetime):
                    result[attr] = value.isoformat()
                elif isinstance(value, date):
                    result[attr] = value.strftime("%Y-%m-%d")
                elif isinstance(value, time):
                    result[attr] = value.strftime("%H:%M:%S")
                elif isinstance(value, Base):
                    result[attr] = value.as_dict()
                else:
                    result[attr] = value
        return result

    pass


class Department(Base):
    __tablename__ = "department"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    users: Mapped[Optional[List["UserAccount"]]] = relationship("UserAccount")


class Role(Base):
    __tablename__ = "role"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    permissions: Mapped[List["RolePermission"]] = relationship("RolePermission")


class Permission(Base):
    __tablename__ = "permission"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    roles: Mapped[Optional[List["Role"]]] = relationship("RolePermission")


class RolePermission(Base):
    __tablename__ = "role_permission"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[Role] = mapped_column(String, ForeignKey("role.name", onupdate="CASCADE", ondelete="CASCADE"),
                                       nullable=False)
    permission: Mapped[Permission] = mapped_column(String, ForeignKey("permission.id", onupdate="CASCADE",
                                                                      ondelete="CASCADE"),
                                                   nullable=False)


class UserType(enum.Enum):
    active = "active"
    suspend = "suspend"
    deleted = "deleted"


class IdentityType(enum.Enum):
    cccd = "cccd"
    cmnd = "cmnd"
    hc = "hc"


class UserAccount(Base):
    __tablename__ = "user_account"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, nullable=False, index=True, unique=True)
    password: Mapped[str] = mapped_column(String, nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String, ForeignKey("department.name"), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String, ForeignKey("role.name"), nullable=True)
    line_manager: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    firstname: Mapped[str] = mapped_column(String, nullable=False)
    middlename: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lastname: Mapped[str] = mapped_column(String, nullable=False)
    gender: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, index=True, unique=True)
    status: Mapped[str] = mapped_column(Enum(UserType, name="user_type"), nullable=False)
    identity: Mapped[str] = mapped_column(String, nullable=False, index=True, unique=True)
    identity_type: Mapped[str] = mapped_column(Enum(IdentityType, name="identity_type"), nullable=False)
    enable_2_verification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class ActiveUserType(enum.Enum):
    pending = "pending"
    active = "active"
    expired = "expired"
    cancelled = "cancelled"


class ActiveUser(Base):
    __tablename__ = "active_user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String,
                                          ForeignKey("user_account.username", onupdate='CASCADE', ondelete='CASCADE'),
                                          nullable=False)
    otp: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Enum(ActiveUserType, name="active_user_type"), nullable=False)
    expired_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)


class UserImage(Base):
    __tablename__ = "user_image"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String,
                                          ForeignKey("user_account.username", onupdate='CASCADE', ondelete='CASCADE'),
                                          nullable=False)
    image: Mapped[str] = mapped_column(String, nullable=False)
    image_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class UserToken(Base):
    __tablename__ = "user_token"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String,
                                          ForeignKey("user_account.username", onupdate='CASCADE', ondelete='CASCADE'),
                                          nullable=False)
    token: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    expired_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class FormProductivity(enum.Enum):
    no_productivity = "Không tính công"
    productivity = "Tính công"
    half_productivity = "Nữa ngày công"


class FormStatus(enum.Enum):
    pending = "Chờ duyệt"
    approved = "Đã duyệt"
    cancelled = "Không duyệt"


class FormPhase(enum.Enum):
    director_approved = "Director Approved"
    authorized_person_approved = "Authorized Person Approved"
    direct_manager_approved = "Direct Manager Approved"


class FormType(enum.Enum):
    leave_request = "Leave Request"
    absentee = "Absentee"
    job_overtime = "Job Overtime"
    check_in_out = "Check In Out"
    shift_change = "Shift Change"
    shift_overtime = "Shift Overtime"
    shift_registration = "Shift Registration"
    business_trip_request = "Business Trip Request"
    work_mode_request = "Work Mode Request"
    resignation = "Resignation"


class FormReason(Base):
    __tablename__ = "form_reason"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    productivity: Mapped[Optional[str]] = mapped_column(String, nullable=True,
                                                        default=FormProductivity.no_productivity.name)
    form_type: Mapped[str] = mapped_column(String, nullable=False)


class Form(Base):
    __tablename__ = "form"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    form_status: Mapped[str] = mapped_column(Enum(FormStatus, name="form_status"), nullable=False,
                                             default=FormStatus.pending)
    form_phase: Mapped[str] = mapped_column(Enum(FormPhase, name="form_phase"), nullable=False)
    form_type: Mapped[str] = mapped_column(Enum(FormType, name="form_type"), nullable=False)
    reason: Mapped[int] = mapped_column(Integer, ForeignKey("form_reason.id", onupdate='CASCADE'),
                                        nullable=False)
    form_reason: Mapped[FormReason] = relationship("FormReason", foreign_keys=[reason])
    productivity: Mapped[str] = mapped_column(Enum(FormProductivity), nullable=False)
    department: Mapped[str] = mapped_column(String, ForeignKey("department.name", onupdate='CASCADE'),
                                            nullable=False)
    role: Mapped[str] = mapped_column(String, ForeignKey("role.name", onupdate='CASCADE'),
                                      nullable=False)
    created_user: Mapped[str] = mapped_column(String, ForeignKey("user_account.username", onupdate='CASCADE'),
                                              nullable=False)
    created_user_obj: Mapped[UserAccount] = relationship("UserAccount", foreign_keys=[created_user])
    assigned_user: Mapped[str] = mapped_column(String,
                                               ForeignKey("user_account.username", onupdate='CASCADE'),
                                               nullable=False)
    assigned_user_obj: Mapped[UserAccount] = relationship("UserAccount", foreign_keys=[assigned_user])
    description: Mapped[str] = mapped_column(String, nullable=True)
    note: Mapped[str] = mapped_column(String, nullable=True)
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    details: Mapped[List["FormDetail"]] = relationship("FormDetail")


class FormDetail(Base):
    __tablename__ = "form_detail"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    form: Mapped[int] = mapped_column(Integer, ForeignKey("form.id", ondelete='CASCADE'), nullable=False)
    from_time: Mapped[time] = mapped_column(Time, nullable=False)
    to_time: Mapped[time] = mapped_column(Time, nullable=False)
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    to_date: Mapped[date] = mapped_column(Date, nullable=False)
