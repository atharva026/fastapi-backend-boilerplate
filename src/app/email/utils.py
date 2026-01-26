import os
from src.app.core.config import config
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Setup Jinja2 Environment
jinja_env = Environment(
    loader=FileSystemLoader(os.path.join(config.BASE_DIR, "templates")),
    autoescape=select_autoescape(["html", "xml"])
)

def render_email_template(template_name: str, context: dict) -> str:
    template = jinja_env.get_template(template_name)
    return template.render(context)
