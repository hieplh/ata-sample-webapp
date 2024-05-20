import os
import random
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Annotated

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

from config import as_form
from db import models
from db.database import get_db
from features.user_account import user_account_service
from features.user_account.user_account_service import encrypt_password, register_identity_with_service, \
    confirm_registration


@as_form
class UserAccount(BaseModel):
    username: str
    password: str
    department: str | None = None
    role: str | None = None
    line_manager: str | None = None
    firstname: str
    middlename: str | None = None
    lastname: str
    gender: str
    email: str
    status: str = models.UserType.suspend
    identity: str
    identity_type: str


class UserAccountRequest(UserAccount):
    images: list[str] = []


mail_body = """
<table
  style="
    width: 100% !important;
    border-collapse: collapse;
    border-spacing: 0;
    table-layout: fixed;
    min-width: 100%;
    color: #0a0836;
    font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Oxygen,
      Ubuntu, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;
    font-size: 14px;
    line-height: 1.5;
    margin: 0;
    padding: 0;
    border: 0;
  "
  height="100%"
  bgcolor="#f6fafb"
>
  <tbody>
    <tr style="padding: 0">
      <td
        style="
          border-collapse: collapse !important;
          word-break: break-word;
          min-width: 100%;
          width: 100% !important;
          margin: 0;
          padding: 20px 10px 30px;
        "
        align="center"
        valign="top"
      >
        <table
          style="
            width: 580px;
            border-collapse: collapse;
            border-spacing: 0;
            table-layout: auto;
            border-radius: 10px;
            padding: 0;
            border: 0;
          "
          bgcolor="#fff"
        >
          <tbody>
            <tr style="padding: 0">
              <td
                style="
                  border-collapse: collapse !important;
                  word-break: break-word;
                  padding: 30px 40px;
                "
                class="m_-9147650361660214470content"
                align="left"
                valign="top"
              >
                <table
                  border="0"
                  cellpadding="0"
                  cellspacing="0"
                  width="100%"
                  style="
                    border-collapse: collapse;
                    border-spacing: 0;
                    table-layout: auto;
                    padding: 0;
                    border: 0;
                  "
                >
                  <tbody>
                    <tr style="padding: 0">
                      <td
                        align="left"
                        valign="middle"
                        style="
                          border-collapse: collapse !important;
                          word-break: break-word;
                          padding: 0;
                        "
                      >
                        <h1
                          style="
                            word-break: normal;
                            font-size: 18px;
                            font-weight: 700;
                            line-height: 21px;
                            padding-bottom: 10px;
                            margin: 0;
                          "
                        >
                          Welcome
                          <a
                            href="mailto:{{user_mail}}"
                            style="color: #00b08c !important"
                            target="_blank"
                            >{{user_mail}}</a
                          >!
                        </h1>
                        <p
                          style="
                            font-size: 14px;
                            padding-bottom: 10px;
                            margin: 0;
                          "
                        >
                          Thank you for signing up for Sample App.
                        </p>
                        <p
                          style="
                            font-size: 14px;
                            padding-bottom: 10px;
                            margin: 0;
                          "
                        >
                          Verify your email address by clicking the button
                          below.
                        </p>
                      </td>
                    </tr>
                    <tr style="padding: 0">
                      <td
                        align="center"
                        valign="middle"
                        style="
                          border-collapse: collapse !important;
                          word-break: break-word;
                          padding: 25px 0 35px;
                        "
                      >
                        <table
                          border="0"
                          cellpadding="0"
                          cellspacing="0"
                          width="335"
                          class="m_-9147650361660214470button-block"
                          style="
                            border-collapse: separate;
                            border-spacing: 0;
                            table-layout: auto;
                            width: auto;
                            padding: 0;
                            border: 0;
                          "
                        >
                          <tbody>
                            <tr style="padding: 0">
                              <td
                                align="center"
                                valign="middle"
                                class="m_-9147650361660214470button"
                                style="
                                  border-collapse: collapse !important;
                                  word-break: break-word;
                                  border-radius: 25px;
                                  padding: 10px 25px;
                                "
                                bgcolor="#00b08c"
                              >
                                <a
                                  href="http://{{host}}:{{port}}/active_user/{{user_username}}/{{user_otp}}"
                                  style="
                                    color: #fff !important;
                                    display: block;
                                    font-size: 14px;
                                    font-weight: 700;
                                    text-decoration: none;
                                  "
                                  target="_blank"
                                  data-saferedirecturl="https://www.google.com/url?q=https://mt-link.mailtrap.io/cl/%2BddnirdWvk4nOHyUTk%252FP52QE82LQCGE%2BzVlCi75epLWRj28ZBzS9MHvp2kT%252FYXooyZFMpUDNBxngfWM%252F30wWvcF5SQJoKI0hGXeC3Cvk46Ye5aXWGz3i4rnwEG1gCOpx6VyUIz7MgP8MHq9tSOo8LvXi2ClteXnJGSsmszzkHk%252FU5vbh2ezh5AzlQ%2B4%252FBReSx60ikeE6iVY1xmTkgfIf%252FOubwbw7Lb2Yr3456jNEMUCdSoAbJAl%2BfRbnOT0yCnlLdgyH8Viqfdi6gYpWl99QtgH1Q1JqvGZnXpJ7OsXKOQ1bcS1QT1RngciOaoCwKMZ%252F5pft%252FqIfJ6E3wiRDhYwZypuTD1mU7R1vRvEn2ZVw%2BHZF8Unx%2BFKECHsF6YFUQas%3D--y0Nxhd%252FcQC1JcwVo--d%252FTrk49p%252FwMJiNGplWXpuQ%3D%3D&amp;source=gmail&amp;ust=1711426923877000&amp;usg=AOvVaw0Qddna-HrdkSGLwDEopiwd"
                                  >Confirm my account</a
                                >
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </td>
                    </tr>
                    <tr style="padding: 0">
                      <td
                        align="left"
                        valign="middle"
                        style="
                          border-collapse: collapse !important;
                          word-break: break-word;
                          padding: 0;
                        "
                      >
                        <p
                          style="
                            font-size: 14px;
                            padding-bottom: 10px;
                            margin: 0;
                          "
                        >
                          Note that unverified accounts are automatically
                          deleted 30 days after signup.
                        </p>
                        <p
                          style="
                            font-size: 14px;
                            padding-bottom: 10px;
                            margin: 0;
                          "
                        >
                          If you didn't request this, please ignore this email.
                        </p>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>
            <tr style="padding: 0">
              <td
                style="
                  border-collapse: collapse !important;
                  word-break: break-word;
                  padding: 0 40px 30px;
                "
                class="m_-9147650361660214470inner-footer"
                align="left"
                valign="middle"
              >
                <table
                  style="
                    width: 50%;
                    border-collapse: collapse;
                    border-spacing: 0;
                    table-layout: auto;
                    padding: 0;
                    border: 0;
                  "
                >
                  <tbody>
                    <tr style="padding: 0">
                      <td
                        style="
                          border-collapse: collapse !important;
                          word-break: break-word;
                          border-top-width: 1px;
                          border-top-color: #e4e4e9;
                          border-top-style: solid;
                          font-size: 12px;
                          line-height: 1.5;
                          padding: 20px 0 0;
                        "
                        align="left"
                        valign="middle"
                      >
                        <strong>Sincerely,</strong><br />
                        <strong>Sample-App Team</strong><br />
                        <a
                          href="mailto:mailtrap@demomailtrap.com"
                          rel="noopener noreferrer"
                          style="color: #00b08c !important"
                          target="_blank"
                          >mailtrap@demomailtrap.com</a
                        >
                      </td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>
          </tbody>
        </table>
      </td>
    </tr>
    <tr>
      <td><br /></td>
    </tr>
    <tr style="padding: 0">
      <td
        style="
          border-collapse: collapse !important;
          word-break: break-word;
          padding: 0 10px 10px;
        "
        align="center"
        valign="top"
      >
        <table
          style="
            width: 580px;
            border-collapse: collapse;
            border-spacing: 0;
            table-layout: auto;
            padding: 0;
            border: 0;
          "
        >
          <tbody>
            <tr style="padding: 0">
              <td
                style="
                  border-collapse: collapse !important;
                  word-break: break-word;
                  color: #8d8c9f;
                  font-size: 11px;
                  padding: 0;
                "
                class="m_-9147650361660214470footer"
                align="center"
                valign="top"
              >
                <table
                  style="
                    width: 100%;
                    border-collapse: collapse;
                    border-spacing: 0;
                    table-layout: auto;
                    color: #8d8c9f;
                    font-size: 11px;
                    padding: 0;
                    border: 0;
                  "
                  class="m_-9147650361660214470footer"
                >
                  <tbody>
                    <tr style="padding: 0">
                      <td
                        style="
                          border-collapse: collapse !important;
                          word-break: break-word;
                          padding: 0;
                        "
                        class="m_-9147650361660214470footer-section"
                        align="left"
                        valign="middle"
                      >
                        Freelancer<br />
                        71/4 Cộng Hòa, phường 4, Tân Bình<br />
                        Tân Bình, HCM
                      </td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>
          </tbody>
        </table>
      </td>
    </tr>
  </tbody>
</table>
"""


def route(app: FastAPI):
    @app.post("/register", status_code=HTTPStatus.CREATED)
    async def register(db: Annotated[Session, Depends(get_db)], background_tasks: BackgroundTasks,
                       request: UserAccountRequest):
        try:
            # create account
            images = request.images
            request.__delattr__('images')
            request.password = encrypt_password(request.password)
            user_account = models.UserAccount(**request.model_dump())
            user_account.department = 'IT Department'
            user_account.role = 'developer'
            db.add(user_account)
            db.flush()

            # create otp to active account
            otp = random.randint(1000, 9999)
            db.add(models.ActiveUser(username=request.username, otp=otp, status=models.ActiveUserType.pending,
                                     expired_at=datetime.now() + timedelta(hours=24), attempts=1))

            # store images
            await user_account_service.store_images(db, request.username, images)

            db.commit()

            # send mail
            background_tasks.add_task(confirm_registration, subject=os.getenv("MAIL_SUBJECT"), body=mail_body,
                                      receiver_email=os.getenv("MAIL_RECEIVER"), user_username=request.username,
                                      otp=otp)

            return {"message": "Registered successfully"}
        except Exception as e:
            db.rollback()
            print("register: " + f"{e}")
            raise HTTPException(status_code=400, detail=f"{e}")

    @app.get("/resend-email/{username}")
    async def resend_email(db: Annotated[Session, Depends(get_db)], background_tasks: BackgroundTasks,
                           username: str):
        try:
            active_user = db.query(models.ActiveUser).filter(models.ActiveUser.username == username,
                                                             models.ActiveUser.status != models.ActiveUserType.active) \
                .first()
            active_user.otp = random.randint(1000, 9999)
            background_tasks.add_task(confirm_registration, subject=os.getenv("MAIL_SUBJECT"),
                                      body=mail_body,
                                      receiver_email=os.getenv("MAIL_RECEIVER"),
                                      user_username=active_user.username,
                                      otp=active_user.otp
                                      )

            db.commit()
            return {"message": "Resend email successfully"}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"{e}")

    @app.get("/active_user/{username}/{otp}")
    def active_user(db: Annotated[Session, Depends(get_db)], background_tasks: BackgroundTasks, username: str,
                    otp: int):
        try:
            err_msg = ""
            user_account = db.query(models.UserAccount).filter(models.UserAccount.username == username).first()
            active_user = (db.query(models.ActiveUser).filter(models.ActiveUser.username == username,
                                                              models.ActiveUser.status == models.ActiveUserType.pending) \
                           .first())

            # check null - user not fount
            if active_user is None:
                err_msg = "User not found"

            # check attempt otp - max 3 attempts
            elif active_user.attempts > 3:
                active_user.status = models.ActiveUserType.cancelled
                err_msg = "Otp has been cancelled"

            # check lifetime of otp
            elif active_user.expired_at < datetime.now():
                active_user.status = models.ActiveUserType.expired
                active_user.attempts = active_user.attempts + 1
                err_msg = "Otp has been expired"

            # check otp
            elif otp != active_user.otp:
                active_user.attempts = active_user.attempts + 1
                err_msg = "Otp does not match"

            # change active status - confirm activated account
            if not err_msg:
                active_user.status = models.ActiveUserType.active
                user_account.status = models.UserType.active

            db.commit()

            if err_msg:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
            else:
                db.refresh(user_account)

                # fetch all images of activated user to register to third-party
                user_images = db.query(models.UserImage).filter(models.UserImage.username == username).all()

                # register face image with identified data at third-party
                background_tasks.add_task(register_identity_with_service, user_account=user_account,
                                          images=user_account_service.get_filename_and_content_type_from_model(
                                              user_images),
                                          retry_count=0)

                return {"message": "Activated account successfully"}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"{e}")
