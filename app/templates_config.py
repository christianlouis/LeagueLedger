#!/usr/bin/env python3
from fastapi.templating import Jinja2Templates
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from starlette.templating import _TemplateResponse
from datetime import datetime
from typing import Any

BASE_DIR = Path(__file__).resolve().parent

# Create a Jinja2 Environment with the 'jinja2.ext.do' extension
class MyJinjaTemplates(Jinja2Templates):
    def __init__(self, directory: str, **kwargs: Any):
        super().__init__(directory=directory, **kwargs)
        self.env.add_extension('jinja2.ext.do')
        self.env.globals['now'] = datetime.now  # Add 'now' function

# Create templates object that can be imported elsewhere
templates = MyJinjaTemplates(directory=str(BASE_DIR / "templates"))

# Register a context processor to add current_user to all templates
templates.env.globals["get_current_user"] = lambda: None  # Will be overridden at runtime
