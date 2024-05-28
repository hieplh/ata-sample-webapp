from datetime import time, date
from typing import Annotated

from fastapi import FastAPI, Depends, UploadFile, Form, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette import status

from db import models, schemas
from db.database import get_db
from features.security.token import Token, validate_token
from features.user_account import user_account_service


class CreateFormDetailRequest(BaseModel):
    from_time: time
    to_time: time
    from_date: date
    to_date: date


class UpdateFormDetailRequest(CreateFormDetailRequest):
    pass


class FormRequest(BaseModel):
    reason: int
    productivity: str
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
    details: list[UpdateFormDetailRequest]


class CreateFormResponse(schemas.Form):
    details: list[schemas.FormDetail] = []

    class Config:
        orm_mode: True


class AllFormsResponse(BaseModel):
    total_count: int = 0
    data: list[schemas.Form] = []


def route(app: FastAPI):
    @app.get("/forms/{type}/count")
    async def count_all(current_user: Annotated[Token, Depends(validate_token)],
                        db: Annotated[Session, Depends(get_db)], type: str):

        match type:
            case 'request':
                query_statement = f"""
                    SELECT
                        SUM(CASE WHEN form_status = 'pending' AND created_user = '{current_user.username}' THEN 1 ELSE 0 END) AS pending,
                        SUM(CASE WHEN form_status = 'approved' AND created_user = '{current_user.username}' THEN 1 ELSE 0 END) AS approved,
                        SUM(CASE WHEN form_status = 'cancelled' AND created_user = '{current_user.username}' THEN 1 ELSE 0 END) AS cancelled
                    FROM form;
                """
            case 'approve':
                query_statement = f"""
                   SELECT
                        SUM(CASE WHEN form_status = 'pending' AND assigned_user = '{current_user.username}' THEN 1 ELSE 0 END) AS pending,
                        SUM(CASE WHEN form_status = 'approved' AND assigned_user = '{current_user.username}' THEN 1 ELSE 0 END) AS approved,
                        SUM(CASE WHEN form_status = 'cancelled' AND assigned_user = '{current_user.username}' THEN 1 ELSE 0 END) AS cancelled
                    FROM form;
                """
            case 'department':
                query_statement = f"""
                    SELECT
                        SUM(CASE WHEN form_status = 'pending' AND department = '{current_user.department}' THEN 1 ELSE 0 END) AS pending,
                        SUM(CASE WHEN form_status = 'approved' AND department = '{current_user.department}' THEN 1 ELSE 0 END) AS approved,
                        SUM(CASE WHEN form_status = 'cancelled' AND department = '{current_user.department}' THEN 1 ELSE 0 END) AS cancelled
                    FROM form;
                """
            case default:
                query_statement = f"""
                    SELECT
                        SUM(CASE WHEN form_status = 'pending' THEN 1 ELSE 0 END) AS pending,
                        SUM(CASE WHEN form_status = 'approved' THEN 1 ELSE 0 END) AS approved,
                        SUM(CASE WHEN form_status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled
                    FROM form;
                """

        result = db.execute(text(query_statement)).mappings().fetchone()
        response = {k: result[k] if result[k] is not None else 0 for k in result}
        response['all'] = sum(response.values())
        return response

    @app.get("/forms/{type}/{form_status}", response_model=AllFormsResponse)
    async def get_all_forms_by_type_and_status(current_user: Annotated[Token, Depends(validate_token)],
                                               db: Annotated[Session, Depends(get_db)],
                                               type: str, form_status: str,
                                               page: int = 0, page_size: int = 20):
        offset = page * page_size if page >= 1 else 0
        is_all_status = 1 if form_status == 'all' else 0
        match type:
            case "request":
                return {
                    "total_count": db.query(models.Form).filter(models.Form.created_user == current_user.username,
                                                                (
                                                                        1 == is_all_status or models.Form.form_status == form_status)).count(),
                    "data": (db.query(models.Form).filter(models.Form.created_user == current_user.username,
                                                          (
                                                                  1 == is_all_status or models.Form.form_status == form_status))
                             .order_by(models.Form.created.desc()).offset(offset).limit(page_size).all())
                }
            case "approve":
                return {
                    "total_count": db.query(models.Form).filter(models.Form.assigned_user == current_user.username,
                                                                (
                                                                        1 == is_all_status or models.Form.form_status == form_status)).count(),
                    "data": (db.query(models.Form).filter(models.Form.assigned_user == current_user.username,
                                                          (
                                                                  1 == is_all_status or models.Form.form_status == form_status))
                             .order_by(models.Form.created.desc()).offset(offset).limit(page_size).all())
                }
            case "department":
                return {
                    "total_count": db.query(models.Form).filter(models.Form.department == current_user.department,
                                                                (
                                                                        1 == is_all_status or models.Form.form_status == form_status)).count(),
                    "data": (db.query(models.Form).filter(models.Form.department == current_user.department,
                                                          (
                                                                  1 == is_all_status or models.Form.form_status == form_status))
                             .order_by(models.Form.created.desc()).offset(offset).limit(page_size).all())
                }
            case default:
                return {}

    @app.get("/forms/{form_status}", response_model=AllFormsResponse)
    async def get_all_forms_by_type(current_user: Annotated[Token, Depends(validate_token)],
                                    db: Annotated[Session, Depends(get_db)],
                                    form_status: str, page: int = 0, page_size: int = 20):
        offset = page * page_size if page >= 1 else 0
        is_all_status = 1 if form_status == 'all' else 0
        return {
            "total_count": db.query(models.Form).filter(
                1 == is_all_status or models.Form.form_status == form_status).count(),
            "data": (db.query(models.Form).filter(1 == is_all_status or models.Form.form_status == form_status)
                     .order_by(models.Form.created.desc()).offset(offset).limit(page_size).all())
        }

    @app.get("/form/{form_id}", response_model=schemas.Form | None)
    async def get(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)],
                  form_id: int):
        form = db.get_one(models.Form, form_id)
        form.form_type = form.form_type.name
        return form

    @app.get("/form/{form_id}/detail", response_model=list[schemas.FormDetail])
    async def get_detail(current_user: Annotated[Token, Depends(validate_token)],
                         db: Annotated[Session, Depends(get_db)],
                         form_id: int):
        return db.get_one(models.Form, form_id).details

    @app.post("/form", status_code=status.HTTP_201_CREATED, response_model=CreateFormResponse)
    async def create(current_user: Annotated[Token, Depends(validate_token)], db: Annotated[Session, Depends(get_db)],
                     request: CreateFormRequest):
        try:
            # create form
            form = models.Form(form_type=request.form_type, department=request.department, role=request.role,
                               description=request.description, note=request.note,
                               reason=request.reason, productivity=request.productivity,
                               created_user=request.created_user, assigned_user=request.assigned_user)
            if "lead" or "leader" or "head" in request.role.lower():
                form.form_phase = models.FormPhase.director_approved.name
            else:
                form.form_phase = models.FormPhase.direct_manager_approved.name
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
                if not isinstance(value, list):
                    setattr(form, var, value) if value else None

            """ 
                For quick and ease to implement update details of form
                Delete all old records then insert new ones 
            """
            # delete all old details record
            deleted_form_details = [detail.id for detail in form.details]
            db.query(models.FormDetail).filter(models.FormDetail.id.in_(deleted_form_details)).delete(
                synchronize_session=False)

            # re-create form detail
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

    @app.put("/form/confirm", response_model=list[schemas.Form])
    async def assigned_user_confirm(current_user: Annotated[Token, Depends(validate_token)],
                                    db: Annotated[Session, Depends(get_db)],
                                    form_id: Annotated[list[int], Form()], form_status: Annotated[str, Form()],
                                    image: UploadFile | None = None):
        try:
            form = db.query(models.Form).filter(models.Form.id.in_(form_id),
                                                models.Form.assigned_user == current_user.username).all()
            # only assigned user is able to use this api
            # if form.assigned_user != current_user.username:
            if len(form) != len(form_id):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="You do not have permission to perform this action.")

            is_enable_2_verification = db.get_one(models.UserAccount, current_user.user_id).enable_2_verification
            if is_enable_2_verification:
                response_identity = await user_account_service.identity_with_service(image)
                if response_identity is None:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                        detail="Face id is not existed")

                identity_user = response_identity.get("identification_id")
                # double check assigned user with third-party
                if identity_user != current_user.username:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                        detail="Verify face is failed")

            for f in form:
                f.form_status = form_status
            db.commit()
            return form
        except Exception as e:
            db.rollback()
            raise e
