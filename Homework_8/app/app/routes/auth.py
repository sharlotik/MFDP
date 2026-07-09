import hashlib
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from auth.authenticate import authenticate_cookie, authenticate
from auth.jwt_handler import create_access_token
from database.database import get_session
from services.auth.loginform import LoginForm
from services.crud import user as UsersService
from database.config import get_settings
from typing import Dict
from models.user import User

settings = get_settings()
auth_route = APIRouter()
templates = Jinja2Templates(directory="view")

@auth_route.post("/token")
async def login_for_access_token(response: Response, form_data: OAuth2PasswordRequestForm=Depends(), session=Depends(get_session)) -> dict[str, str]:    
    user_exist = UsersService.get_user_by_email(form_data.username, session)
    if user_exist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")
    
    input_hash = hashlib.sha256(form_data.password.encode()).hexdigest()
    if input_hash == user_exist.password:
        access_token = create_access_token(user_exist.email)
        response.set_cookie(
            key=settings.COOKIE_NAME, 
            value=f"Bearer {access_token}", 
            httponly=True
        )
        return {settings.COOKIE_NAME: access_token, "token_type": "bearer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid details passed."
    )

@auth_route.get("/login", response_class=HTMLResponse)
async def login_get(request: Request, error: str = None, redirect_to: str = None):
    # ИСПРАВЛЕНО: Новый синтаксис
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "errors": [error] if error else [],
            "redirect_to": redirect_to,
            "username": "",
            "password": ""
        }
    )

@auth_route.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, session=Depends(get_session)):
    form = LoginForm(request)
    await form.load_data()
    if await form.is_valid():
        try:
            user = UsersService.get_user_by_email(email=form.username, session=session)
            
            if not user:
                form.errors.append("User with this email doesn't exist. Please signup")
                # ИСПРАВЛЕНО: Новый синтаксис
                return templates.TemplateResponse(
                    request=request,
                    name="login.html",
                    context={
                        "redirect_to": "/auth/signup",
                        "errors": form.errors,
                        "username": form.username,
                        "password": ""
                    }
                )

            input_hash = hashlib.sha256(form.password.encode()).hexdigest()
            if input_hash == user.password:
                access_token = create_access_token(user.email)            
                response = RedirectResponse("/private", status_code=status.HTTP_303_SEE_OTHER)
                response.set_cookie(
                    key=settings.COOKIE_NAME, 
                    value=f"Bearer {access_token}", 
                    httponly=True
                )
                print(f"[green]Login successful for {user.email}")
                return response
            else:
                form.errors.append("Incorrect password")
                # ИСПРАВЛЕНО: Новый синтаксис
                return templates.TemplateResponse(
                    request=request,
                    name="login.html",
                    context={
                        "errors": form.errors,
                        "username": form.username,
                        "password": ""
                    }
                )

        except Exception as e:
            print(f"[red]Database Error: {e}")
            form.errors.append("Error in connection to database")
            # ИСПРАВЛЕНО: Новый синтаксис
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={
                    "errors": form.errors,
                    "username": form.username,
                    "password": ""
                }
            )

    # ИСПРАВЛЕНО: Новый синтаксис
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "errors": form.errors,
            "username": form.username,
            "password": ""
        }
    )

@auth_route.get("/signup", response_class=HTMLResponse)
async def signup_get(request: Request, error: str = None, message: str = None, redirect_to: str = None):
    # ИСПРАВЛЕНО: Новый синтаксис
    return templates.TemplateResponse(
        request=request,
        name="signup.html",
        context={
            "errors": [error] if error else [],
            "messages": [message] if message else [],
            "redirect_to": redirect_to,
            "username": "",
            "password": ""
        }
    )

@auth_route.post("/signup", response_class=HTMLResponse)
async def signup_post(request: Request, session=Depends(get_session)):
    form = LoginForm(request)
    await form.load_data()
    
    # Считываем object_id из формы, если он там есть, иначе ставим None
    form_data = await request.form()
    object_id_raw = form_data.get("object_id")
    object_id = int(object_id_raw) if (object_id_raw and str(object_id_raw).isdigit()) else None

    if await form.is_valid():
        existing_user = UsersService.get_user_by_email(email=form.username, session=session)
    
        if existing_user:
            form.errors.append("User with this email exists already")
            return templates.TemplateResponse(
                request=request,
                name="signup.html",
                context={
                    "redirect_to": "/auth/login",
                    "errors": form.errors,
                    "username": form.username,
                    "password": ""
                }
            )
            
        try:
            # Создаем пользователя с явным указанием object_id (база больше не будет ругаться)
            new_user = User(
                email=form.username, 
                password=hashlib.sha256(form.password.encode()).hexdigest(),
                object_id=object_id  # Передаем число или None
            )

            UsersService.create_user(new_user, session)
            form.messages.append(f"Created new user: {new_user.email}. Please, login")
            return templates.TemplateResponse(
                request=request,
                name="signup.html",
                context={
                    "redirect_to": "/auth/login",
                    "errors": form.errors,
                    "messages": form.messages,
                    "username": form.username,
                    "password": ""
                }
            )
           
        except Exception as e:
            print(f"[red]Database Error: {e}")
            form.errors.append("Error in connection to database")
            return templates.TemplateResponse(
                request=request,
                name="signup.html",
                context={
                    "errors": form.errors,
                    "username": form.username,
                    "password": ""
                }
            )

    return templates.TemplateResponse(
        request=request,
        name="signup.html",
        context={
            "errors": form.errors,
            "username": form.username,
            "password": ""
        }
    )

@auth_route.get("/logout", response_class=HTMLResponse)
async def logout_get():
    response = RedirectResponse(url="/")
    response.delete_cookie(settings.COOKIE_NAME)
    return response