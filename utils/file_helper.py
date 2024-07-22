import os


path = "resources/images"


def delete_folder(folder_path_name):
    if os.path.exists(folder_path_name) and not os.listdir(folder_path_name):
        os.rmdir(folder_path_name)


def delete_file(file_path_name, folder_path_name):
    final_path = path + "/" + folder_path_name + "/" + file_path_name
    final_path = final_path.replace("//", "/").replace("\\\\", "/")

    # delete image
    if os.path.exists(final_path):
        os.remove(final_path)

    # delete empty folder stores sub-folders
    delete_folder(path + "/" + folder_path_name)


def create_folder(folder_path):
    if not os.path.exists(path + "/" + folder_path):
        os.makedirs(path + "/" + folder_path)


def create_file(folder_path: str, filename: str, file_content: bytes):
    # create folder to store images
    create_folder(folder_path)

    final_path = f"{path}/{folder_path}/{filename}"
    with open(final_path, 'wb') as new_image_file:
        new_image_file.write(file_content)
