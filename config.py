import inspect
from configparser import ConfigParser
from typing import Type

from fastapi import Form
from pydantic import BaseModel


def load_config(filename: str, section: str):
    """ Load config file """
    parser = ConfigParser()
    parser.read(filename, "UTF-8")

    config = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            config[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return config


def as_form(cls: Type[BaseModel]):
    """
    Adds an as_form class method to decorated models. The as_form class method
    can be used with FastAPI endpoints
    """

    new_params = []
    for keys, field in cls.__fields__.items():
        new_params.append(
            inspect.Parameter(
                keys,
                inspect.Parameter.POSITIONAL_ONLY,
                default=Form(field.default) if not field.is_required() else Form(...),
            )
        )

    async def _as_form(**data):
        return cls(**data)

    sig = inspect.signature(_as_form)
    sig = sig.replace(parameters=new_params)
    _as_form.__signature__ = sig
    setattr(cls, "as_form", _as_form)
    return cls
