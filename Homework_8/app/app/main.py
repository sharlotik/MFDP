from database.config import get_settings
from database.database import get_session, init_db, get_database_engine
from services.crud.user import get_all_users, create_user
from sqlmodel import Session
from models.event import Event
from models.user import User
from models.transaction import Transaction
from models.wallet import Wallet


if __name__ == "__main__":
    settings = get_settings()
    print(settings.APP_NAME)
    print(settings.API_VERSION)
    print(f'Debug: {settings.DEBUG}')
    
    print(settings.DB_HOST)
    print(settings.DB_NAME)
    print(settings.DB_USER)
    
    init_db(drop_all=True)
    print('Init db has been success')
    
      test_user_1 = User(id=1, email="Nick@gmail.com",
                    password_hash=hashlib.sha256("password123".encode()).hexdigest())
    test_user_2 = User(id=2, email="Peter@gmail.com",    
                    password_hash=hashlib.sha256("password456".encode()).hexdigest())
    test_user_3 = User(id=3, email="birdwatcher@gmail.com", 
                    password_hash=hashlib.sha256("password789".encode()).hexdigest())

           
    test_event_1 = Event(id = 1, title='test', image='test', description='test', 
                        creator = test_user_1)
    test_event_2 = Event(id = 2, title='test', image='test', description='test', 
                        creator = test_user_2)
    
    test_user_1.events.append(test_event_1)
    test_user_2.events.append(test_event_2)
    
    engine = get_database_engine()
    
    with Session(engine) as session:
        create_user(test_user_1, session)
        create_user(test_user_2, session)
        create_user(test_user_3, session)
        users = get_all_users(session)
        
    print('-------')
    print(f'Id локального пользователя: {id(test_user_1)}')
    print(f'Id пользователя из БД: {id(users[0])}')
    print(f'Id одинаковые: {id(test_user_1) == id(users[0])}')

    print('-------')
    print('Пользователи из БД:')        
    for user in users:
        print(user)
        print('Пользовательские события:')
        if user.event_count == 0:
            print('Пользователь не имеет событий')
        else:
            for event in user.events:
                print(event)

