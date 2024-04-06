from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import models, schemas
from db.database import get_db
from features.security.token import Token, validate_token


class RoleRequest(BaseModel):
    name: str
    description: str | None = None
    permissions: list[str]


def route(app: FastAPI):
    @app.get("/roles", response_model=list[schemas.Role])
    async def get_all(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)]):
        return db.query(models.Role).all()

    @app.get("/role/{role_name}", response_model=schemas.Role | None)
    async def get(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)],
                  role_name: str):
        return db.query(models.Role).filter(models.Role.name == role_name).first()

    @app.post("/role", response_model=schemas.Role)
    async def create(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)],
                     request: RoleRequest):
        try:
            role_permissions = [models.RolePermission(role=request.name, permission=r) for r in request.permissions]
            role = models.Role(name=request.name, description=request.description, permissions=role_permissions)
            db.add(role)
            db.commit()
            db.refresh(role)
            return role
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"{e}")
