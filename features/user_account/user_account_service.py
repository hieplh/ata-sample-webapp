import base64
import json
import os
import random
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import bcrypt
import requests
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


def register_identity_with_service(user_account: models.UserAccount,
                                   images: list[tuple[str, str]],
                                   retry_count: int = 0):
    if len(images) == 0:
        return

    try:
        url = f"{os.getenv('FACE_HOST')}/service/face_recognize/register"
        face_token = os.getenv("FACE_TOKEN")
        headers = {"Authorization": f"Bearer {face_token}"}

        # init data content
        data = user_account.as_dict()
        data.__delitem__("password") if data.get("password") else None

        # init face images
        folder = "resources/images/"
        files = [
            ("files", (
                image[0], open(folder + "/" + image[0], mode='rb'),
                image[1])) for image in images
        ] if len(images) else []

        response = (requests.post(url,
                                  headers=headers,
                                  files=files,
                                  data={"identification_id": data.get("username"),
                                        "content": json.dumps(data)}
                                  )
                    )
        return response.json()
    except Exception as e:
        print(f"register_identity_with_service: {e}")
        # retry make http call if failed, max 3 times
        if retry_count < 1:
            register_identity_with_service(user_account, images, retry_count + 1)
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
        response = (requests.delete(os.getenv("FACE_HOST") + "/service/face_recognize/" + user_account.username,
                                    headers=headers)
                    )

        return response.json()
    except Exception as e:
        print(f"delete_identity_with_service: {e}")
        # retry make http call if failed, max 3 times
        if retry_count < 1:
            await delete_identity_with_service(user_account, retry_count + 1)
        else:
            raise e


async def identity_with_service(username: str, image: UploadFile, retry_count: int = 0):
    try:
        face_token = os.getenv("FACE_TOKEN")
        headers = jsonable_encoder(
            {
                "Authorization": f"Bearer {face_token}"
            }
        )
        data = {"identification_id": username}
        files = {"file": (image.filename, await image.read(), image.content_type)}
        response = (requests.post(os.getenv("FACE_HOST") + "/service/face_recognize/identify",
                                  headers=headers,
                                  files=files,
                                  data=data
                                  )
                    )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"identity_with_service: {e}")
        return None
    except Exception as e:
        print(f"identity_with_service: {e}")
        # retry make http call if failed, max 3 times
        if retry_count < 1:
            await identity_with_service(image, retry_count + 1)
        else:
            raise e


async def store_images(dbConnection: Session, username: str, images=None):
    if images is None:
        images = []

    path = "resources/images"
    for image in images:
        image_arr = image.split(",")
        image_header = image_arr[0]  # image_header example: data:image/jpeg;base64
        image_content = image_arr[1]
        # extract content_type from image_header
        image_content_type = image_header.split(";")[0].split("/")[1]
        filename = f"{username}_{random.randint(0, 9999)}.{image_content_type}"
        final_path = path + "/" + filename

        with open(final_path, 'wb') as f:
            # convert string to bytes to create image
            f.write(base64.b64decode(image_content))

        # insert image to images
        dbConnection.add(models.UserImage(username=username, image=filename, image_type=image_content_type))


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


def confirm_registration(user_username: str, otp: int, receiver_email: str, subject: str, body: str):
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
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(os.getenv("MAIL_HOST"), int(os.getenv("MAIL_PORT"))) as server:
            server.starttls(context=context)
            server.login(username, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
    except Exception as e:
        print(f"confirm_registration | Error: {e}")
