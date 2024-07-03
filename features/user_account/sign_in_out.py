from datetime import datetime, timedelta
from typing import Annotated

from fastapi import FastAPI, status, HTTPException, Depends, UploadFile, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import schemas, models
from db.database import get_db
from db.models import UserToken, UserAccount
from features.security.token import Token, validate_token, generate_token
from features.user_account import user_account_service
from features.user_account.user_account_service import check_password


class LoginRequest(BaseModel):
    username: str
    password: str


class LogoutRequest(BaseModel):
    username: str
    token: str


def route(app: FastAPI):
    @app.post("/login", response_model=schemas.UserToken | dict)
    async def login(db: Annotated[Session, Depends(get_db)], user: LoginRequest):
        try:
            user_account = db.query(UserAccount).filter(UserAccount.username == user.username,
                                                        UserAccount.status == models.UserType.active) \
                .first()

            if user_account is not None:
                if not check_password(user.password, user_account.password):
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                        detail="Username or Password is incorrect")

                # check if user is enabled 2 verification or not
                # if enabled, return nothing, returned token will be depended on login_by_face
                if user_account.enable_2_verification:
                    images_count = db.query(models.UserImage).filter(models.UserImage.username == user_account.username).count()
                    if images_count > 0:
                        return {}

                # fetch current token if existed
                user_token = db.query(UserToken).filter(UserToken.username == user.username,
                                                        UserToken.expired_at > datetime.now()) \
                    .first()
                if user_token is not None:
                    return user_token

                # generate new token if not existed
                expire_time = datetime.utcnow() + timedelta(days=3)  # Expired after 3 days
                token = generate_token(user_account, expire_time)
                user_token = UserToken(username=user.username, token=token, expired_at=expire_time)
                db.add(user_token)
                db.commit()
                db.refresh(user_token)
                return user_token
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or Password is incorrect")
        except Exception as e:
            db.rollback()
            raise e

    @app.post("/login/face", response_model=schemas.UserToken)
    async def login_by_identification(db: Annotated[Session, Depends(get_db)], username: Annotated[str, Form()],
                                      face_image: UploadFile):
        response_identity = await user_account_service.identity_with_service(username, face_image)
        if response_identity is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Face identification is incorrect")

        try:
            user_account = db.query(UserAccount).filter(UserAccount.username == username,
                                                        UserAccount.status == models.UserType.active) \
                .first()

            verified_user = response_identity.get("identification_id")
            if user_account.username != verified_user:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Face identification is incorrect")

            # fetch current token if existed
            user_token = db.query(UserToken).filter(UserToken.username == user_account.username,
                                                    UserToken.expired_at > datetime.now()) \
                .first()
            if user_token is not None:
                return user_token

            # generate new token if not existed
            expire_time = datetime.utcnow() + timedelta(days=3)  # Expired after 3 days
            token = generate_token(user_account, expire_time)
            user_token = UserToken(username=user_account.username, token=token, expired_at=expire_time)
            db.add(user_token)
            db.commit()
            db.refresh(user_token)
            return user_token
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"{e}")

    @app.post("/logout")
    async def logout(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)]):
        try:
            # delete user token
            user_token = db.query(UserToken).filter(UserToken.username == current_user.username).first()
            db.delete(user_token)
            db.commit()
            return {"message": "Logout successful"}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"{e}")
