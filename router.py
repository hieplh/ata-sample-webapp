from fastapi import FastAPI

from features.department import department_controller
from features.form import form_controller, form_reason, form_type
from features.role import role_controller, permission_controller
from features.user_account import user_account_controller, registration, sign_in_out


def route_all(app: FastAPI):
    # department
    department_controller.route(app)

    # role
    permission_controller.route(app)
    role_controller.route(app)

    # user account
    registration.route(app)
    sign_in_out.route(app)
    user_account_controller.route(app)

    # form
    form_reason.route(app)
    form_type.route(app)
    form_controller.route(app)
