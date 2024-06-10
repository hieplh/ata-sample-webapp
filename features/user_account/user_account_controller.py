import re
from http.client import HTTPException
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session
from starlette import status

from db import models, schemas
from db.database import get_db
from features.security.token import Token, validate_token
from features.user_account import user_account_service
from features.user_account.user_account_service import encrypt_password


class UpdateUserImageRequest(BaseModel):
    id: int | None = None
    content: str


class UserAccount(BaseModel):
    username: str | None = None
    password: str | int | None = None
    department: str | None = None
    role: str | None = None
    line_manager: str | None = None
    firstname: str | None = None
    middlename: str | None = None
    lastname: str | None = None
    gender: str | None = None
    email: str | None = None
    status: str | None = None
    identity: str | None = None
    identity_type: str | None = None
    enable_2_verification: bool | None = None
    updated_images: list[UpdateUserImageRequest] | None = None
    deleted_images: list[int] | None = None


def route(app: FastAPI):
    @app.post("/me", response_model=schemas.UserAccount)
    async def me(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)]):
        return db.get_one(models.UserAccount, current_user.user_id)

    @app.get("/user/images", response_model=list[schemas.UserImage])
    async def get_images(current_user: Annotated[Token, Depends(validate_token)],
                         db: Annotated[Session, Depends(get_db)]):
        user_images = db.query(models.UserImage).filter(models.UserImage.username == current_user.username).all()
        for user_image in user_images:
            user_image.image = user_account_service.image_to_base64_png(user_image.image, user_image.image_type)
        return user_images

    @app.get("/user/{data}", response_model=schemas.UserAccount | None)
    async def get(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)],
                  data: str):
        # accept id, email or identity to find identified user
        id = int(data) if data.isdigit() else None
        email = data if re.search(r'^[\w\.-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$', data) else None
        identity = data if id is None and email is None else None
        return db.query(models.UserAccount).filter(or_(models.UserAccount.id == id, models.UserAccount.email == email,
                                                       models.UserAccount.identity == identity)).first()

    @app.get("/users", response_model=list[schemas.UserAccount])
    async def get_all(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)]):
        return db.query(models.UserAccount).order_by(models.UserAccount.firstname.desc()).all()

    @app.put("/user", response_model=schemas.UserAccount)
    async def update(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)],
                     background_tasks: BackgroundTasks,
                     request: UserAccount):
        try:
            updated_images = request.updated_images
            deleted_images = request.deleted_images
            request.__delattr__("updated_images")
            request.__delattr__("deleted_images")

            # accept id, email or identity to find identified user
            user = db.get_one(models.UserAccount, current_user.user_id)
            for var, value in vars(request).items():
                if var == "password" and value:
                    value = encrypt_password(str(value))
                setattr(user, var, value) if value is not None else None

            # store images
            if updated_images is not None and len(updated_images) > 0:
                updated_images = [
                    {
                        "id": image.id,
                        "content": user_account_service.extract_based64_encoded_image(
                            current_user.username,
                            image.content)
                    }
                    for
                    image in updated_images]

                for image in updated_images:
                    if image["id"] is not None:
                        user_image = db.get_one(models.UserImage, image["id"])
                        image["content"]["filename"] = user_image.image
                        user_account_service.update_image(db, image["id"], image["content"])
                    else:
                        user_account_service.store_image(db, current_user.username, image["content"])

                # register face image with identified data at third-party
                background_tasks.add_task(user_account_service.register_identity_with_service,
                                          user_account=user,
                                          images=user_account_service.get_filename_and_content_type_from_upload(
                                              updated_images),
                                          retry_count=0)

            if deleted_images is not None and len(deleted_images) > 0:
                for image_id in deleted_images:
                    if image_id is not None:
                        # fetch all images of deleted user
                        deleted_image = db.get_one(models.UserImage, image_id)
                        db.delete(deleted_image)
                        user_account_service.delete_image(image_name=deleted_image.image)

            db.commit()
            db.refresh(user)

            return user
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"{e}")

    @app.delete("/user/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete(current_user: Annotated[Token, Depends(validate_token)],
                     db: Annotated[Session, Depends(get_db)],
                     user_id: int):
        try:
            # fetch user is deleted
            deleted_user = db.get_one(models.UserAccount, user_id)
            deleted_user.status = models.UserType.deleted

            # fetch all images of deleted user
            deleted_images = db.query(models.UserImage).filter(models.UserImage.username == deleted_user.username).all()

            # delete images
            user_account_service.delete_images(deleted_images)
            # delete images in db
            for deleted_image in deleted_images:
                db.delete(deleted_image)

            # delete tokens
            user_tokens = db.query(models.UserToken).filter(models.UserToken.username == deleted_user.username).all()
            for token in user_tokens:
                db.delete(token)

            await user_account_service.delete_identity_with_service(deleted_user)

            db.commit()
            return {"message": "User is deleted"}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"{e}")
