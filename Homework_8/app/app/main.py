import hashlib
from sqlmodel import Session

from database.config import get_settings
from database.database import get_session, init_db, get_database_engine
from services.crud.user import get_all_users, create_user

from api import app

if __name__ == "__main__":
    from models.event import Event
    from models.user import User
    from models.transaction import Transaction
    from models.wallet import Wallet
    from models.object import Object  # Импортируем модель объекта/компании

    settings = get_settings()
    print(f"App Name: {settings.APP_NAME}")
    
    init_db(drop_all=True)
    print('Init db has been success')
    
    test_company = Object(id=1, name="My Cafe", address="New York", category="restaurant", place_id="1") 
    
    p1 = hashlib.sha256("password123".encode()).hexdigest()
    p2 = hashlib.sha256("password456".encode()).hexdigest()
    p3 = hashlib.sha256("password789".encode()).hexdigest()


    test_user_1 = User(email="Nick@gmail.com", password=p1, company=test_company)
    test_user_2 = User(email="Peter@gmail.com", password=p2, company=test_company)
    test_user_3 = User(email="birdwatcher@gmail.com", password=p3, company=test_company)
           
    test_event_1 = Event(text="Отличный сервис, всё понравилось!", status="completed", creator=test_user_1)
    test_event_2 = Event(text="Пиццу несли слишком долго.", status="completed", creator=test_user_2)
    
    test_user_1.events.append(test_event_1)
    test_user_2.events.append(test_event_2)
    
    engine = get_database_engine()
    
    with Session(engine) as session:
        session.add(test_company) 
        
        create_user(test_user_1, session)
        create_user(test_user_2, session)
        create_user(test_user_3, session)
        
        session.commit()  
        users = get_all_users(session)
        
    print('-------')
    print('Пользователи и их компании из БД:')        
    for user in users:
        # Проверяем, что связь с компанией работает
        company_title = user.company.name if user.company else "Нет компании"
        print(f"User: {user.email} | Company: {company_title}")