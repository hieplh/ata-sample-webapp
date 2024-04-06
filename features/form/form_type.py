from typing import Annotated

from fastapi import FastAPI, Depends

from db import models
from features.security.token import Token, validate_token


def route(app: FastAPI):
    @app.get("/form/type")
    async def get_all(current_user: Annotated[Token, Depends(validate_token)]):
        return ({"name": e.name, "value": e.value} for e in models.FormType)
