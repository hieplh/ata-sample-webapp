from typing import Annotated

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from db import models, schemas
from db.database import get_db
from features.security.token import Token, validate_token


def route(app: FastAPI):
    @app.get("/form/reason", response_model=list[schemas.FormReason])
    async def get_all(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)]):
        return db.query(models.FormReason).all()
