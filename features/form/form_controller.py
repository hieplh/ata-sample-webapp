from datetime import time, date
from typing import Annotated

from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

from db import models, schemas
from db.database import get_db
from features.security.token import Token, validate_token


class CreateFormDetailRequest(BaseModel):
    from_time: time
    to_time: time
    from_date: date
    to_date: date
    reason: str
    productivity: str


class UpdateFormDetailRequest(CreateFormDetailRequest):
    id: int


class FormRequest(BaseModel):
    form_type: str
    department: str
    role: str
    description: str | None = None
    note: str | None = None
    assigned_user: str


class CreateFormRequest(FormRequest):
    created_user: str
    details: list[CreateFormDetailRequest]


class UpdateFormRequest(FormRequest):
    id: int
    form_status: str
    details: list[UpdateFormDetailRequest]


def route(app: FastAPI):
    @app.get("/forms", response_model=list[schemas.Form])
    async def get_all(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)]):
        return db.query(models.Form).filter(models.Form.created_user == current_user.username).order_by(
            models.Form.created.desc()).all()

    @app.get("/forms/assigned", response_model=list[schemas.Form])
    async def get_all_assigned(current_user: Annotated[Token, Depends(validate_token)],
                               db: Annotated[Session, Depends(get_db)]):
        return db.query(models.Form).filter(models.Form.assigned_user == current_user.username).order_by(
            models.Form.created_user.desc()).all()

    @app.get("/form/{form_id}", response_model=schemas.Form | None)
    async def get(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)],
                  form_id: int):
        return db.get_one(models.Form, form_id)

    @app.get("/form/{form_id}/detail", response_model=list[schemas.FormDetail])
    async def get_detail(current_user: Annotated[Token, Depends(validate_token)],
                         db: Annotated[Session, Depends(get_db)],
                         form_id: int):
        return db.get_one(models.Form, form_id).details

    @app.post("/form", status_code=status.HTTP_201_CREATED, response_model=schemas.Form)
    async def create(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)],
                     request: CreateFormRequest):
        try:
            # create form
            form = models.Form(form_type=request.form_type, department=request.department, role=request.role,
                               description=request.description, note=request.note,
                               created_user=request.created_user, assigned_user=request.assigned_user)
            if "lead" or "leader" or "head" in request.role.lower():
                form.form_phase = models.FormPhase.director_approved
            else:
                form.form_phase = models.FormPhase.direct_manager_approved
            db.add(form)
            db.flush()

            # create form detail
            form_details = [
                models.FormDetail(form=form.id, **detail.model_dump())
                for detail in request.details]
            db.add_all(form_details)

            db.commit()
            db.refresh(form)
            return form
        except Exception as e:
            db.rollback()
            raise e

    @app.put("/form", response_model=schemas.Form)
    async def update(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)],
                     request: UpdateFormRequest):
        try:
            form = db.get_one(models.Form, request.id)
            for var, value in vars(request).items():
                if var == "form_status" and current_user.username == request.assigned_user:
                    form.form_status = value
                elif isinstance(value, list):
                    [setattr(detail, detail_var, detail_value) for detail in form.details
                     for request_detail in request.details
                     if detail.id == request_detail.id
                     for detail_var, detail_value in vars(request_detail).items()]
                else:
                    setattr(form, var, value) if value else None

            db.commit()
            db.refresh(form)
            return form
        except Exception as e:
            db.rollback()
            raise e
