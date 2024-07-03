import base64
import io
import json
import os
import random
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import bcrypt
import requests
from PIL import Image
from fastapi import UploadFile
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from db import models

path = "resources/images"


def image_to_base64_png(image_path: str, image_type: str) -> str:
    # with Image.open(f"{path}/{image_path}") as img:
    #     buffered = io.BytesIO()
    #     img.save(buffered, format=image_type)
    #     img_bytes = buffered.getvalue()
    # img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    # return img_base64
    with open(f"{path}/{image_path}", "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def encrypt_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(password: str, encrypted_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), encrypted_password.encode('utf-8'))


def extract_based64_encoded_image(username: str, encoded_image: str):
    if len(encoded_image) == 0:
        return None

    image_arr = encoded_image.split(",")
    image_header = image_arr[0]  # image_header example: data:image/jpeg;base64
    image_content = image_arr[1]
    # extract content_type from image_header
    image_content_type = image_header.split(";")[0].split("/")[1]
    return {"filename": f"{username}_{random.randint(0, 9999)}.{image_content_type}",
            "image_header": image_header,
            "image_content": image_content,
            "image_content_type": image_content_type}


def extract_based64_encoded_images(username: str, encoded_images: list[str]):
    if len(encoded_images) == 0:
        return []

    images = []
    return [images.append(extract_based64_encoded_image(username, image)) for image in encoded_images]


def get_filename_and_content_type_from_model(user_images: list[models.UserImage]) -> list[tuple[str, str]]:
    return [(user_image.image,
             (
                 user_image.image_type if user_image.image_type is not None else "image/png"))
            for user_image in user_images] if len(user_images) else []


def get_filename_and_content_type_from_upload(upload_images: list[UploadFile | dict[str, int | None]]) -> tuple[str, str]:
    result = []
    if upload_images is not None:
        for file in upload_images:
            if isinstance(file, UploadFile):
                if file.size == 0:
                    continue

                result.append((file.filename, file.content_type))
            elif isinstance(file, dict):
                image = file["content"]
                result.append(
                    (image["filename"], image["image_content_type"], file["service_image_id"], image["image_content"]))

    return result


def get_identity_images_with_service(username: str, retry_count: int = 0):
    try:
        url = f"{os.getenv('FACE_HOST')}/service/face_recognize/images/{username}"
        face_token = os.getenv("FACE_TOKEN")
        headers = {"Authorization": f"Bearer {face_token}"}

        response = (requests.get(url, headers=headers))
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"get_identity_images_with_service: {e}")
        # retry make http call if failed, max 3 times
        if retry_count < 1:
            get_identity_images_with_service(username, retry_count + 1)
        else:
            return []


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


def update_identity_with_service(user_account: models.UserAccount,
                                 images: list[tuple[str, str]],
                                 retry_count: int = 0):
    if len(images) == 0:
        return

    try:
        url = f"{os.getenv('FACE_HOST')}/service/face_recognize/update"
        face_token = os.getenv("FACE_TOKEN")
        headers = {"Authorization": f"Bearer {face_token}", "Content-Type": "application/json"}

        # init data content
        images_payload = []
        for image in images:
            images_payload.append({"image_old_id": image[2], "image_new_name": image[0], "image_new": image[3]})
        payload = {"identification_id": user_account.username,
                   "images": images_payload}

        response = (requests.put(url,
                                 headers=headers,
                                 json=payload
                                 ))
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
        files = {"image": (image.filename, await image.read(), image.content_type)}
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


def delete_image(fullpath_image: str | None = None, image_name: str | None = None):
    if image_name is not None and len(image_name) > 0:
        # delete image by its name
        if os.path.exists(path):
            os.remove(path + "/" + image_name)

    if fullpath_image is not None and len(fullpath_image) > 0:
        # delete image by its fullpath
        if os.path.exists(fullpath_image):
            os.remove(fullpath_image)


def store_image(dbConnection: Session, username: str, image=None):
    if image is None:
        return

    final_path = path + "/" + image["filename"]

    with open(final_path, 'wb') as f:
        # convert string to bytes to create image
        f.write(base64.b64decode(image["image_content"]))

    # insert image to images
    dbConnection.add(
        models.UserImage(username=username, image=image["filename"],
                         image_type=image["image_content_type"]))


def update_image(image=None):
    if image is None:
        return

    final_path = path + "/" + image["filename"]

    # delete the old image before insert new one
    delete_image(fullpath_image=final_path)

    with open(final_path, 'wb') as f:
        # convert string to bytes to create image
        f.write(base64.b64decode(image["image_content"]))


def delete_images(user_images: list[models.UserImage]):
    if len(user_images) == 0:
        return

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
