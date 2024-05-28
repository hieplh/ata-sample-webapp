import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from db import models

load_dotenv()

# Access the environment variables
db_username = os.getenv('DB_PORTGRES_USERNAME')
db_password = os.getenv('DB_PORTGRES_PASSWORD')
db_port = os.getenv('DB_PORTGRES_PORT')
db_host = os.getenv('DB_PORTGRES_HOST')
db_name = os.getenv('DB_PORTGRES_DBNAME')

# Construct the database URL
SQLALCHEMY_DATABASE_URL = f"postgresql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@event.listens_for(models.Department.__table__, "after_create")
def init_department(target, connection, **kw):
    """ Init data the permission table. """
    connection.execute(text(
        f"INSERT INTO {target.name} (name, description, created, last_updated) VALUES "
        f"('IT Department', 'Department for all IT staffs', now(), now()); "
    ))


@event.listens_for(models.Permission.__table__, "after_create")
def init_permission(target, connection, **kw):
    """ Init data the permission table. """
    connection.execute(text(
        f"INSERT INTO {target.name} (id, name, description, created) VALUES "
        f"('READ', 'Read', 'Read permission', now()), "
        f"('WRITE', 'Write', 'Write permission', now());"
    ))


@event.listens_for(models.Role.__table__, "after_create")
def init_role(target, connection, **kw):
    """ Init data the permission table. """
    connection.execute(text(
        f"INSERT INTO {target.name} (name, description, created, last_updated) VALUES "
        f"('developer', '', now(), now()), "
        f"('test', '', now(), now());"
    ))


@event.listens_for(models.RolePermission.__table__, "after_create")
def init_role_permission(target, connection, **kw):
    """ Init data the permission table. """
    connection.execute(text(
        f"INSERT INTO {target.name} (role, permission) VALUES "
        f"('developer', 'READ'), "
        f"('developer', 'WRITE'), "
        f"('test', 'READ');"
    ))


@event.listens_for(models.FormReason.__table__, "after_create")
def init_form_reason(target, connection, **kw):
    """ Init data the form_reason table. """
    connection.execute(text(
        f"INSERT INTO {target.name} (name, description, productivity, form_type) VALUES "
        f"('Nghỉ phép năm', 'Không giới hạn', '{models.FormProductivity.productivity.name}', '{models.FormType.leave_request.name}'), "
        f"('Nghỉ ốm đau (BHXH)', 'Không giới hạn', '{models.FormProductivity.no_productivity.name}', '{models.FormType.leave_request.name}'), "
        f"('Nghỉ kết hôn', 'Không giới hạn', '{models.FormProductivity.productivity.name}', '{models.FormType.leave_request.name}'), "
        f"('Nghỉ vợ sinh (BHXH)', 'Không giới hạn', '{models.FormProductivity.no_productivity.name}', '{models.FormType.leave_request.name}'), "
        f"('Nghỉ không lương', 'Không giới hạn', '{models.FormProductivity.no_productivity.name}', '{models.FormType.leave_request.name}'), "

        f"('Việc cá nhân (không tính công)', 'Không giới hạn', '{models.FormProductivity.no_productivity.name}', '{models.FormType.absentee.name}'), "
        f"('Giải quyết việc Công ty', 'Không giới hạn', '{models.FormProductivity.productivity.name}', '{models.FormType.absentee.name}'), "
        f"('Làm việc tại nhà (WFH)', 'Không giới hạn', '{models.FormProductivity.productivity.name}', '{models.FormType.absentee.name}'), "
        f"('Tham gia khóa đào tạo bên ngoài', 'Không giới hạn', '{models.FormProductivity.productivity.name}', '{models.FormType.absentee.name}'), "
        f"('Nghỉ bù ngày lễ', 'Không giới hạn<break>Khi ngày lễ trùng ngày nghỉ hàng tuần', '{models.FormProductivity.productivity.name}', '{models.FormType.absentee.name}'), "
        f"('Tham gia sự kiện của Công ty ở bên ngoài', 'Không giới hạn', '{models.FormProductivity.no_productivity.name}', '{models.FormType.absentee.name}');"
    ))
