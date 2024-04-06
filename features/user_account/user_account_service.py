import json
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import bcrypt
import httpx
from fastapi import UploadFile
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from db import models


def encrypt_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(password: str, encrypted_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), encrypted_password.encode('utf-8'))


def get_filename_and_content_type_from_model(user_images: list[models.UserImage]) -> list[tuple[str, str]]:
    return [(user_image.image,
             (
                 user_image.image_type if user_image.image_type is not None else "image/png"))
            for user_image in user_images] if len(user_images) else []


def get_filename_and_content_type_from_upload(upload_images: list[UploadFile | None]) -> list[tuple[str, str]]:
    result = []
    if upload_images is not None:
        for file in upload_images:
            if file.size == 0:
                continue

            result.append((file.filename, file.content_type))
    return result


async def register_identity_with_service(user_account: models.UserAccount,
                                         images: list[tuple[str, str]],
                                         retry_count: int = 0):
    try:
        face_token = os.getenv("FACE_TOKEN")
        headers = jsonable_encoder(
            {
                "Authorization": f"Bearer {face_token}"
            }
        )

        # init data content
        data = user_account.as_dict()
        data.__delitem__("password") if data.get("password") else None

        # init face images
        folder = "resources/images/" + data.get("username")
        files = [
            ("files", (
                image[0], open(folder + "/" + image[0], mode='rb'),
                image[1])) for image in images
        ] if len(images) else []

        response = httpx.post(os.getenv("FACE_HOST") + "/service/face_recognize/register", headers=headers,
                              files=files,
                              data={"identification_id": data.get("username"),
                                    "content": json.dumps(data)}) \
            .raise_for_status()

        return response.json()
    except Exception as e:
        print(f"register_identity_with_service: {e}")
        # retry make http call if failed, max 3 times
        if retry_count < 3:
            await register_identity_with_service(user_account, images, retry_count + 1)
        else:
            raise e


async def delete_identity_with_service(user_account: models.UserAccount, retry_count: int = 0):
    try:
        face_token = os.getenv("FACE_TOKEN")
        headers = jsonable_encoder(
            {
                "Authorization": f"Bearer {face_token}"
            }
        )
        response = httpx.delete(os.getenv("FACE_HOST") + "/service/face_recognize/" + user_account.username,
                                headers=headers) \
            .raise_for_status()

        return response.json()
    except Exception as e:
        print(f"delete_identity_with_service: {e}")
        # retry make http call if failed, max 3 times
        if retry_count < 3:
            await delete_identity_with_service(user_account, retry_count + 1)
        else:
            raise e


async def identity_with_service(image: UploadFile, retry_count: int = 0):
    try:
        face_token = os.getenv("FACE_TOKEN")
        headers = jsonable_encoder(
            {
                "Authorization": f"Bearer {face_token}"
            }
        )
        files = {"file": (image.filename, await image.read(), image.content_type)}
        response = httpx.post(os.getenv("FACE_HOST") + "/service/face_recognize/identify",
                              headers=headers,
                              files=files) \
            .raise_for_status()

        return response.json()
    except Exception as e:
        print(f"identity_with_service: {e}")
        # retry make http call if failed, max 3 times
        if retry_count < 3:
            await identity_with_service(image, retry_count + 1)
        else:
            raise e


async def store_images(dbConnection: Session, username: str, files: list[UploadFile | None] = None):
    if files is not None:
        path = "resources/images"
        for file in files:
            if file.size == 0:
                continue

            # insert image to images
            dbConnection.add(models.UserImage(username=username, image=file.filename, image_type=file.content_type))

            # create folder to store images of project_id and service_id
            folder_name = username
            if not os.path.exists(path + "/" + folder_name):
                os.makedirs(path + "/" + folder_name)

            # store image to sub-folder above
            with open(os.path.join(path, folder_name, file.filename), 'wb') as new_image_file:
                new_image_file.write(await file.read())


def delete_images(user_images: list[models.UserImage]):
    if len(user_images) == 0:
        return

    path = "resources/images"
    for user_image in user_images:
        folder_name = user_image.username
        final_folder = path + "/" + folder_name

        # delete image
        if os.path.exists(final_folder):
            os.remove(final_folder + "/" + user_image.image)

            # delete empty folder stores images
            if not os.listdir(final_folder):
                os.rmdir(final_folder)


async def confirm_registration(user_username: str, otp: int, receiver_email: str, subject: str, body: str):
    sender_email = os.getenv('MAIL_SENDER')
    username = os.getenv('MAIL_USERNAME')
    password = os.getenv('MAIL_PASSWORD')

    # Create message container - the correct MIME type is multipart/alternative.
    message = MIMEMultipart('alternative')
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject

    # Add body to email
    body = (body.replace("{{user_mail}}", receiver_email)
            .replace("{{host}}", "localhost")
            .replace("{{port}}", os.getenv("PORT"))
            .replace("{{user_username}}", user_username)
            .replace("{{user_otp}}", str(otp)))
    message.attach(MIMEText(body, "html"))

    # Log in to server using secure context and send email
    context = ssl.create_default_context()
    with smtplib.SMTP(os.getenv("MAIL_HOST"), int(os.getenv("MAIL_PORT"))) as server:
        server.starttls(context=context)
        server.login(username, password)
        server.sendmail(sender_email, receiver_email, message.as_string())
