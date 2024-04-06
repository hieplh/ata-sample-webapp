from datetime import datetime
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

from db import models
from db.database import get_db
from features.security.token import Token, validate_token


class DepartmentRequest(BaseModel):
    name: str
    description: str | None = None


class DepartmentResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created: datetime
    last_updated: datetime


def route(app: FastAPI):
    @app.get("/department/{department_name}", response_model=DepartmentResponse)
    def get(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)],
            department_name: str):
        return db.query(models.Department).filter(models.Department.name == department_name).first()

    @app.get("/departments", response_model=list[DepartmentResponse])
    def get_all(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)]):
        return db.query(models.Department).order_by(models.Department.name.desc()).all()

    @app.post("/department", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
    def create(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)],
               request: DepartmentRequest):
        try:
            department = models.Department(**request.model_dump())
            db.add(department)
            db.commit()
            db.refresh(department)
            return department
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"{e}")
