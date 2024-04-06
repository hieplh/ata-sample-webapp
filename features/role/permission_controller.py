from typing import Annotated

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from db import models, schemas
from db.database import get_db
from features.security.token import Token, validate_token


def route(app: FastAPI):
    @app.get("/permissions", response_model=list[schemas.Permission])
    async def get_all(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)]):
        return db.query(models.Permission).all()

    @app.get("/permissions/{permission_name}", response_model=schemas.Permission)
    async def get(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)],
                  permission_name: str):
        return db.query(models.Permission).filter(models.Permission.name == permission_name).first()
