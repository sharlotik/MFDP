from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from auth.authenticate import authenticate_cookie, authenticate
from auth.hash_password import HashPassword
from auth.jwt_handler import create_access_token
from database.database import get_session
from services.auth.loginform import LoginForm
from services.crud import user as UsersService
from database.config import get_settings
from typing import Dict
from models.user import User

settings = get_settings()
auth_route = APIRouter()
hash_password = HashPassword()
templates = Jinja2Templates(directory="view")

@auth_route.post("/token")
async def login_for_access_token(response: Response, form_data: OAuth2PasswordRequestForm=Depends(), session=Depends(get_session)) -> dict[str, str]:    
    user_exist = UsersService.get_user_by_email(form_data.username, session)
    if user_exist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")
    
    if hash_password.verify_hash(form_data.password, user_exist.password):
        access_token = create_access_token(user_exist.email)
        response.set_cookie(
            key=settings.COOKIE_NAME, 
            value=f"Bearer {access_token}", 
            httponly=True
        )
        
        # return {"access_token": access_token, "token_type": "Bearer"}
        return {settings.COOKIE_NAME: access_token, "token_type": "bearer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid details passed."
    )

@auth_route.get("/login", response_class=HTMLResponse)
async def login_get(request: Request, error: str = None, redirect_to: str = None):
    context = {
        "request": request,
        "errors": [error] if error else [],
        "redirect_to": redirect_to
    }
    return templates.TemplateResponse("login.html", context)

   
@auth_route.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, session=Depends(get_session)):
    form = LoginForm(request)
    await form.load_data()
    if await form.is_valid():
        try:
            user= UsersService.get_user_by_email(email = form.username, session = session)
            
            if not user:
                form.__dict__.get("errors").append(
                    f"User with this email doesn't exist. Please signup")
             #   return RedirectResponse(url="/auth/signup", status_code=302)
                return templates.TemplateResponse("login.html", {
                    "request": request, 
                    "redirect_to": "/auth/signup", 
                    **form.__dict__
                })
              #  new_user = User(
              #      email=form.username, 
              #      password=hash_password.create_hash(form.password) 
              #  )
               # UsersService.create_user(new_user, session)
                #print(f"[yellow]Created new user: {new_user.email}")

            if hash_password.verify_hash(form.password, user.password):
                access_token = create_access_token(user.email)            
                response = RedirectResponse("/", status_code=status.HTTP_302_FOUND)
                response.set_cookie(
                    key=settings.COOKIE_NAME, 
                    value=f"Bearer {access_token}", 
                    httponly=True
                )
                print(f"[green]Login successful for {user.email}")
                return response
            else:
                form.__dict__.get("errors").append("Incorrect password")
                return templates.TemplateResponse("login.html", 
                {"request": request, **form.__dict__})
                #form.__dict__)

        except Exception as e:
            print(f"[red]Database Error: {e}")
            form.__dict__.get("errors").append("Error in connection to database")
            return templates.TemplateResponse("login.html", form.__dict__)
           # import traceback
            #traceback.print_exc()
            #form.__dict__.get("errors").append(f"Dev Error: {e}") 
            #return templates.TemplateResponse("login.html", {"request": request, **form.__dict__})

    return templates.TemplateResponse("login.html", 
    {"request": request, **form.__dict__})
   # form.__dict__)

@auth_route.get("/signup", response_class=HTMLResponse)
async def signup_get(request: Request, error: str = None, message: str = None,
    redirect_to: str = None):
    context = {
        "request": request,
        "errors": [error] if error else [],
        "messages": [message] if message else [],
        "redirect_to": redirect_to
    }
    return templates.TemplateResponse("signup.html", context)

    
@auth_route.post("/signup", response_class=HTMLResponse)
async def signup_post(request: Request, session=Depends(get_session)):
    form = LoginForm(request)
    await form.load_data()
    if await form.is_valid():
        existing_user = UsersService.get_user_by_email(
                email=form.username, session=session)
    
        if existing_user:
            form.errors.append("User with this email exists already")
           # return templates.TemplateResponse("signup.html", 
            #     {"request": request, **form.__dict__})
            return templates.TemplateResponse("signup.html", {
                    "request": request, 
                    "redirect_to": "/auth/login", 
                    **form.__dict__
                })
            
        try:
            new_user = User(
                email=form.username, 
                password=hash_password.create_hash(form.password) 
            )

            UsersService.create_user(new_user, session)
            form.messages.append(f"Created new user: {new_user.email}. Please, login")
            #return RedirectResponse(url="/auth/login", status_code=303)
            return templates.TemplateResponse("signup.html", {
                    "request": request, 
                    "redirect_to": "/auth/login", 
                    **form.__dict__
                })
           
        except Exception as e:
            print(f"[red]Database Error: {e}")
            form.__dict__.get("errors").append("Error in connection to database")
  #  #        return templates.TemplateResponse("signup.html", form.__dict__)
            return templates.TemplateResponse("signup.html", 
                               {"request": request, **form.__dict__})

                
           # import traceback
            #traceback.print_exc()
            #form.__dict__.get("errors").append(f"Dev Error: {e}") 
            #return templates.TemplateResponse("login.html", {"request": request, **form.__dict__})

    
    #return templates.TemplateResponse("signup.html", form.__dict__)
    return templates.TemplateResponse("signup.html", {"request": request, **form.__dict__})


"""
          response = RedirectResponse("/", status.HTTP_302_FOUND)
            await login_for_access_token(response=response, form_data=form, session=session)
            form.__dict__.update(msg="Login Successful!")
            print("[green]Login successful!!!!")
            return response
        except HTTPException:
            form.__dict__.update(msg="")
            form.__dict__.get("errors").append("Incorrect Email or Password")
            return templates.TemplateResponse("login.html", form.__dict__)
    return templates.TemplateResponse("login.html", form.__dict__)
"""

@auth_route.get("/logout", response_class=HTMLResponse)
async def login_get():
    response = RedirectResponse(url="/")
    response.delete_cookie(settings.COOKIE_NAME)
    return response

