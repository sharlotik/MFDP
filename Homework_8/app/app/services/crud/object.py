from sqlmodel import Session, select
from models.object import Object
from typing import Optional

def get_object_by_id(object_id: int, session: Session) -> Optional[Object]:

    try:
        statement = select(Object).where(Object.id == object_id)
        return session.exec(statement).first()
    except Exception as e:
        raise

def create_object(db_object: Object, session: Session) -> Object:

    try:
        session.add(db_object)
        session.commit()
        session.refresh(db_object)
        return db_object
    except Exception as e:
        session.rollback()
        raise