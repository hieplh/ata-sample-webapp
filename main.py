import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.encoders import jsonable_encoder
from starlette import status
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

import router
from db import models
from db.database import engine

load_dotenv()

models.Base.metadata.create_all(bind=engine)
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router.route_all(app)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, e: HTTPException):
    return JSONResponse(
        status_code=e.status_code,
        content=jsonable_encoder({"errMsg": e.detail}),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, e: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder({"errMsg": e.__str__()}),
    )


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=int(os.getenv("PORT", 8000)))
