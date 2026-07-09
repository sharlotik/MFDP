from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Form 
from fastapi import File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from auth.authenticate import authenticate_cookie, authenticate
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
import io
import shutil
import json
import pandas as pd
from services.rm import rm as rm_module
from models.event import Event
from sqlmodel import select
from sqlalchemy.orm import selectinload
import asyncio
from urllib.parse import quote, unquote

# ИМПОРТ ИЗ ВАШЕГО ФАЙЛА event.py
from routes.event import upload_review, retrieve_prediction, ReviewUploadPayload, upload_reviews_via_file

settings = get_settings()
home_route = APIRouter()
templates = Jinja2Templates(directory="view")
UPLOAD_DIR = "../data/images" 

@home_route.get("/", response_class=HTMLResponse)
async def index(request: Request):
    token = request.cookies.get(settings.COOKIE_NAME)
    if token:
        try:
            user = await authenticate_cookie(token)
        except Exception:
            user = None
    else:
        user = None

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "user": user
        }
    )


@home_route.get("/private", response_class=HTMLResponse)
async def index_private(
    request: Request, 
    last_id: int = None,
    review_text: str = "",  # Только для текста одиночного отзыва
    file_msg: str = "",     # ИСПРАВЛЕНО: Отдельная переменная для статуса файла
    batch_ids: str = "",   
    user: str = Depends(authenticate_cookie),
    session = Depends(get_session)
):
    user_identified = UsersService.get_user_by_email(email=user, session=session)
    if not user_identified:
        return RedirectResponse(url="/auth/login")

    balance = WalletService.get_balance_by_user_id(user_id=user_identified.id, session=session)
    
    uploaded_reviews = []
    if batch_ids:
        try:
            id_list = [int(x) for x in batch_ids.split(",") if x.strip()]
            statement = select(Event).where(Event.id.in_(id_list)).order_by(Event.id.asc())
            uploaded_reviews = session.exec(statement).all()
        except Exception as e:
            print(f"Error fetching batch reviews: {e}")

    prediction = None
    confidence = None
    if last_id:
        try:
            status_data = await retrieve_prediction(id=last_id, session=session)
            prediction = status_data["ai_rating"]
            confidence = status_data["confidence"]
        except Exception:
            prediction = "Analyzing... (refresh page)"

    return templates.TemplateResponse(
        request=request,
        name="private.html",
        context={
            "user": user_identified,
            "balance": balance,
            "prediction": prediction,
            "confidence": confidence,
            "current_review_text": unquote(review_text) if review_text else "", # В окно попадет ТОЛЬКО одиночный отзыв
            "file_notification": unquote(file_msg) if file_msg else "",       # ИСПРАВЛЕНО: Уведомление файла отдельно
            "uploaded_reviews": uploaded_reviews,  
            "batch_ids": batch_ids  
        }
    )

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
                txn_type='Deposit',
                amount=amount, 
                session=session
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Internal Server Error {type(e).__name__}: {str(e)}")
    return RedirectResponse(url="/private", status_code=status.HTTP_303_SEE_OTHER)

@home_route.post("/ml/predict")
async def predict_review_rating(
    review_text: str = Form(...),  
    user_email: str = Depends(authenticate_cookie),
    session = Depends(get_session)
):
    user_identified = UsersService.get_user_by_email(email=user_email, session=session)
    if not user_identified:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    try:
        # УПАКОВЫВАЕМ ДАННЫЕ В ВАШУ СХЕМУ ReviewUploadPayload
        payload = ReviewUploadPayload(text=review_text, creator_id=user_identified.id)

        # ОТПРАВЛЯЕМ В ВАШУ РУЧКУ upload_review (она сохранит в БД и отправит задачу воркеру)
        result = await upload_review(payload=payload, session=session)
        
        # ИСПРАВЛЕНО: Добавляем текст отзыва в URL-параметры при редиректе
        return RedirectResponse(
            url=f"/private?last_id={result['event_id']}&review_text={quote(review_text)}", 
            status_code=status.HTTP_303_SEE_OTHER
        )

    except Exception as e:
        print(f"Error during ML task creation: {e}")
        return RedirectResponse(url="/private", status_code=status.HTTP_303_SEE_OTHER)



@home_route.post("/ml/predict-file")
async def predict_file_asynchronously(
    file: UploadFile = File(...),
    user_email: str = Depends(authenticate_cookie),
    session = Depends(get_session)
):
    user_identified = UsersService.get_user_by_email(email=user_email, session=session)
    if not user_identified:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    try:
        contents = await file.read()
        reviews_list = []

        if file.filename.endswith('.txt'):
            text_data = contents.decode("utf-8")
            reviews_list = [line.strip() for line in text_data.split('\n') if line.strip()]
        elif file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
            reviews_list = df.iloc[:, 0].dropna().astype(str).tolist()
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(contents))
            reviews_list = df.iloc[:, 0].dropna().astype(str).tolist()
        else:
            return RedirectResponse(url="/private?file_msg=" + quote("Неподдерживаемый формат файла"), status_code=status.HTTP_303_SEE_OTHER)

        if not reviews_list:
            return RedirectResponse(url="/private?file_msg=" + quote("Файл пустой"), status_code=status.HTTP_303_SEE_OTHER)

        created_ids = []

        for raw_text in reviews_list:
            clean_text = str(raw_text).strip()
            if not clean_text:
                continue
                
            new_event = EventService.create_event(
                image=clean_text, 
                creator_id=user_identified.id,
                session=session
            )
            
            task_worker = {
                "event_id": int(new_event.id),  
                "text": clean_text  
            }
            
            rm_module.send_task(json.dumps(task_worker)) 
            created_ids.append(str(new_event.id))
            
        batch_ids_str = ",".join(created_ids)
        success_msg = f"Файл успешно обработан! Загружено отзывов: {len(created_ids)}."
        
        # ИСПРАВЛЕНО: Передаем в параметре file_msg= вместо review_text=
        return RedirectResponse(
            url=f"/private?file_msg={quote(success_msg)}&batch_ids={batch_ids_str}", 
            status_code=status.HTTP_303_SEE_OTHER
        )

    except Exception as e:
        print(f"[ERROR] Batch file async dispatch failed: {e}")
        return RedirectResponse(
            url="/private?file_msg=" + quote("Ошибка при обработке файла"), 
            status_code=status.HTTP_303_SEE_OTHER
        )

@home_route.get("/history/predictions", response_class=HTMLResponse)
async def predictions_history(
    request: Request, 
    user_email: str = Depends(authenticate_cookie),
    session = Depends(get_session)
):
    user_identified = UsersService.get_user_by_email(user_email, session)
    try:
        statement = select(Event).where(Event.creator_id == user_identified.id).options(
            selectinload(Event.creator)
        ) 
        events = session.exec(statement).all()
        
        return templates.TemplateResponse(
            request=request,
            name="events_history.html",
            context={
                "user": user_identified,
                "events": events
            }
        )
        
    except Exception as e:
        print(f"Error fetching history: {e}")
        return templates.TemplateResponse(
            request=request,
            name="events_history.html",
            context={
                "user": user_identified, 
                "events": []
            }
        )

from models.transaction import Transaction

@home_route.get("/history/transactions", response_class=HTMLResponse)
async def billing_history(
    request: Request, 
    user_email: str = Depends(authenticate_cookie),
    session = Depends(get_session)
):
    user_identified = UsersService.get_user_by_email(user_email, session)
    try:
        statement = select(Transaction).where(Transaction.user_id == user_identified.id)
        transactions = session.exec(statement).all()
        
        return templates.TemplateResponse(
            request=request,
            name="transactions_history.html",
            context={
                "user": user_identified,
                "transactions": transactions
            }
        )
    except Exception as e:
        print(f"Error fetching billing history: {e}")
        return templates.TemplateResponse(
            request=request,
            name="transactions_history.html",
            context={
                "user": user_identified,
                "transactions": []
            }
        )

@home_route.get("/health", response_model=Dict[str, str], summary="Health check endpoint")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}