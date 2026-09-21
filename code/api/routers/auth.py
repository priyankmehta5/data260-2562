import os
import time
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_302_FOUND


router = APIRouter()

TEMPLATE_DIRECTORY = (
    Path(__file__).resolve().parents[1] / "templates"
)

templates = Jinja2Templates(
    directory=str(TEMPLATE_DIRECTORY)
)

VALID_USERNAME = "admin"
VALID_PASSWORD = "password"

IDLE_TIMEOUT_SECONDS = int(
    os.getenv("IDLE_TIMEOUT_SECONDS", "300")
)


def current_user(request: Request):
    return request.session.get("user")


def session_expired(request: Request) -> bool:
    user = current_user(request)
    last_activity = request.session.get("last_activity")

    if not user or last_activity is None:
        return True

    idle_seconds = time.time() - float(last_activity)

    if idle_seconds > IDLE_TIMEOUT_SECONDS:
        request.session.clear()
        return True

    request.session["last_activity"] = time.time()
    return False


@router.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "user": current_user(request)
        }
    )


@router.get("/login")
def login_page(
    request: Request,
    expired: int = 0
):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "user": current_user(request),
            "error": None,
            "expired": bool(expired)
        }
    )


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    if (
        username == VALID_USERNAME
        and password == VALID_PASSWORD
    ):
        request.session.clear()
        request.session["user"] = username
        request.session["last_activity"] = time.time()

        return RedirectResponse(
            url="/dashboard",
            status_code=HTTP_302_FOUND
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "user": None,
            "error": "Invalid username or password.",
            "expired": False
        },
        status_code=401
    )


@router.get("/dashboard")
def dashboard(request: Request):
    if not current_user(request):
        return RedirectResponse(
            url="/login",
            status_code=HTTP_302_FOUND
        )

    if session_expired(request):
        return RedirectResponse(
            url="/login?expired=1",
            status_code=HTTP_302_FOUND
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": current_user(request),
            "timeout_seconds": IDLE_TIMEOUT_SECONDS
        }
    )


@router.get("/logout")
def logout(request: Request):
    request.session.clear()

    return RedirectResponse(
        url="/",
        status_code=HTTP_302_FOUND
    )