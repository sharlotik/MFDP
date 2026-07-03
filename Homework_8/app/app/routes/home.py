from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Form 
from fastapi import File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from auth.authenticate import authenticate_cookie, authenticate
from auth.hash_password import HashPassword
from auth.jwt_handler import create_access_token
from database.database import get_session
from services.auth.loginform import LoginForm
from services.crud import user as UsersService
from services.crud import wallet as WalletService
from services.crud import event as EventService
from services.crud import transaction as TransactionService
from database.config import get_settings
from typing import Dict
from decimal import Decimal
import os
import shutil
import json
from services.rm import rm as rm_module
from models.event import Event
from sqlmodel import select
from sqlalchemy.orm import selectinload

settings = get_settings()
home_route = APIRouter()
hash_password = HashPassword()
templates = Jinja2Templates(directory="view")
UPLOAD_DIR = "../data/images" 

"""
@home_route.get(
    "/", 
    response_model=Dict[str, str],
    summary="Root endpoint",
    description="Returns a welcome message"
)
async def index() -> str:
    
  #  Root endpoint returning welcome message.

   # Returns:
    #    Dict[str, str]: Welcome message

    try:
        return {"message": "Welcome to Event Planner API"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
"""

@home_route.get("/", response_class=HTMLResponse)
async def index(request: Request):
    token = request.cookies.get(settings.COOKIE_NAME)
    if token:
        user = await authenticate_cookie(token)
    else:
        user = None

    context = {
        "user": user,
        "request": request
    }
    return templates.TemplateResponse("index.html", context)

@home_route.get("/private", response_class=HTMLResponse)
async def index_private(
    request: Request, 
    last_id: int = None,  # <--- Добавьте этот параметр!
    user: str = Depends(authenticate_cookie),
    session = Depends(get_session)
):
    user_identified = UsersService.get_user_by_email(email=user, session=session)
    if not user_identified:
        return RedirectResponse(url="/auth/login")

    balance = WalletService.get_balance_by_user_id(user_id=user_identified.id, session=session)
    
    prediction = None
    if last_id:
        event = EventService.get_event_by_id(last_id, session) 
        if event:
            prediction = event.prediction if event.prediction else "Analyzing... (refresh page)"

    context = {
        "user": user_identified,
        "balance": balance,
        "prediction": prediction, 
        "request": request
    }
    return templates.TemplateResponse("private.html", context)

@home_route.post("/wallet/topup")
async def deposit_money(
    request: Request,
    amount: Decimal = Form(...), 
    user: str = Depends(authenticate_cookie),
    session = Depends(get_session)
):
    user_identified = UsersService.get_user_by_email(email=user, session=session)
    
    if user_identified:
        try:
            TransactionService.create_transaction(
            user_id=user_identified.id, 
            txn_type = 'Deposit',
            amount=amount, 
            session=session)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Internal Server Error {type(e).__name__}: {str(e)}")
    return RedirectResponse(url="/private", status_code=status.HTTP_303_SEE_OTHER)

@home_route.post("/ml/predict")
async def predict_bird(
    file: UploadFile = File(...),
    user_email: str = Depends(authenticate_cookie),
    session = Depends(get_session)
):
    user_identified = UsersService.get_user_by_email(email=user_email, session=session)
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    try:
        new_event = EventService.create_event(
                image = file_path, 
                creator_id = user_identified.id,
                session = session)

        task_worker = {
            "event_id": new_event.id,  
            "image_path": file_path
        }
        rm_module.send_task(json.dumps(task_worker))
                   
        return RedirectResponse(
            url=f"/private?last_id={new_event.id}", 
            status_code=status.HTTP_303_SEE_OTHER
        )

    except Exception as e:
        print(f"Error during ML task creation: {e}")
        # Если ошибка — просто возвращаем на страницу без ID события
        return RedirectResponse(url="/private", status_code=status.HTTP_303_SEE_OTHER)

@home_route.get("/history/predictions", response_class=HTMLResponse)
async def predictions_history(
    request: Request, 
    user_email: str = Depends(authenticate_cookie),
    session = Depends(get_session)
):
    user_identified = UsersService.get_user_by_email(user_email, session)
    try:
        # Добавлена вторая скобка в конце: одна для selectinload, вторая для .options()
        statement = select(Event).where(Event.creator_id == user_identified.id).options(
            selectinload(Event.creator)
        ) 
        events = session.exec(statement).all()
        
        return templates.TemplateResponse("events_history.html", {
            "request": request,
            "user": user_identified,
            "events": events
        })
        
    except Exception as e:
        print(f"Error fetching history: {e}")
        # ОБЯЗАТЕЛЬНО передаем user сюда, чтобы Jinja2 не выдала UndefinedError
        return templates.TemplateResponse("events_history.html", {
            "request": request, 
            "user": user_identified, 
            "events": []
        })

from models.transaction import Transaction # Не забудь импортировать модель

@home_route.get("/history/transactions", response_class=HTMLResponse)
async def billing_history(
    request: Request, 
    user_email: str = Depends(authenticate_cookie),
    session = Depends(get_session)
):
    user_identified = UsersService.get_user_by_email(user_email, session)
    
    try:
        # Ищем транзакции по user_id (проверь имя поля в своей модели)
        statement = select(Transaction).where(Transaction.user_id == user_identified.id)
        transactions = session.exec(statement).all()
        
        return templates.TemplateResponse("transactions_history.html", {
            "request": request,
            "user": user_identified,
            "transactions": transactions
        })
    except Exception as e:
        print(f"Error fetching billing history: {e}")
        return templates.TemplateResponse("transactions_history.html", {
            "request": request, 
            "user": user_identified,
            "transactions": []
        })


@home_route.get(
    "/health",
    response_model=Dict[str, str],
    summary="Health check endpoint",
    description="Returns service health status"
)
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint for monitoring.

    Returns:
        Dict[str, str]: Health status message
    
    Raises:
        HTTPException: If service is unhealthy
    """
    try:
        # Add actual health checks here
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail="Service unavailable"
        )

