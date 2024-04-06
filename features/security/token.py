import os
from datetime import datetime
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError, BaseModel
from sqlalchemy.orm import Session
from typing_extensions import Any

from db import models
from db.database import get_db

""" Auth Token - Token for authenticate on using Application """


class Token(BaseModel):
    user_id: int
    username: str
    department: str | None = None
    role: str | None = None
    firstname: str
    lastname: str
    middlename: str | None = None
    email: str
    expired_at: datetime

    def __init__(self, /, **data: Any):
        super().__init__(**data)
        self.user_id = int(data.get("user_id")) if isinstance(data.get("user_id"), str) else data.get("user_id")
        self.username = data.get("username")
        self.department = data.get("department")
        self.role = data.get("role")
        self.firstname = data.get("firstname")
        self.lastname = data.get("lastname")
        self.middlename = data.get("middlename")
        self.email = data.get("email")
        self.expired_at = datetime.fromisoformat(data.get("expired_at")) if isinstance(data.get("expired_at"),
                                                                                       str) else data.get("expired_at")

    def to_serializable_dict(self):
        # Convert object to a dict that can be serialized to JSON
        return {
            'user_id': self.user_id,
            'username': self.username,
            'department': self.department,
            'role': self.role,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'middlename': self.middlename,
            'email': self.email,
            'expired_at': self.expired_at.isoformat()
        }


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def generate_token(user: models.UserAccount, expired_at: datetime) -> str:
    # init basic token info
    token = Token(**{
        'user_id': user.id,
        'username': user.username,
        'department': user.department,
        'role': user.role,
        'firstname': user.firstname,
        'lastname': user.lastname,
        'middlename': user.middlename,
        'email': user.email,
        'expired_at': expired_at})
    encoded_jwt = jwt.encode(token.to_serializable_dict(), os.getenv("SECRET_KEY"),
                             algorithm=os.getenv("SECURITY_ALGORITHM"))
    return encoded_jwt


async def validate_token(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    try:
        # Decode JWT token to get user object
        payload = jwt.decode(token,
                             os.getenv("SECRET_KEY"),
                             algorithms=[os.getenv("SECURITY_ALGORITHM")])

        user_token = db.query(models.UserToken).filter(models.UserToken.username == payload.get("username")).first()
        if user_token is None:
            raise HTTPException(status_code=403, detail="User does not exist")

        errMsg = ""
        # convert str to datetime and compare
        if user_token.expired_at < datetime.now():
            errMsg = "Token expired"

        if user_token.token != token:
            errMsg = "User does not exist"

        if errMsg:
            db.delete(user_token)
            raise HTTPException(status_code=403, detail=f"{errMsg}")

        db.commit()
        return Token(**payload)
    except (jwt.PyJWTError, ValidationError) as e:
        db.rollback()
        raise HTTPException(
            status_code=403,
            detail=e.__str__()
        )
