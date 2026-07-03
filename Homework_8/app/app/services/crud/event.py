from models.event import Event, EventUpdate, EventBase, EventCreate
from models.model import Model
from models.wallet import Wallet 
from models.transaction import Transaction
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
from decimal import Decimal


def get_all_events(session: Session) -> List[Event]:
    """
    Retrieve all events.
    
    Args:
        session: Database session
    
    Returns:
        List[Event]: List of all events
    """
    try:
        statement = select(Event)
        events = session.exec(statement).all()
        return events
    except Exception as e:
        raise

def get_event_by_id(event_id: int, session: Session) -> Optional[Event]:
    """
    Get event by ID.
    
    Args:
        event_id: Event ID to find
        session: Database session
    
    Returns:
        Optional[Event]: Found event or None
    """
    try:
        statement = select(Event).where(Event.id == event_id)
        event = session.exec(statement).first()
        return event
    except Exception as e:
        raise

def update_event(event_id: int, event_update: EventUpdate, session: Session) -> Optional[Event]:
    """
    Update existing event.
    
    Args:
        event_id: Event ID to update
        event_update: New event data
        session: Database session
    
    Returns:
        Optional[Event]: Updated event or None if not found
    """
    try:
        event = get_event_by_id(event_id, session)
        if not event:
            return None

        event_data = event_update.dict(exclude_unset=True)
        for key, value in event_data.items():
            setattr(event, key, value)

        session.add(event)
        session.commit()
        session.refresh(event)
        return event
    except Exception as e:
        session.rollback()
        raise

"""
def create_event(event_data: EventCreate, creator_id: int, 
                    model : Model, session: Session) -> Event:
    predict = model.predict(input_data = event_data.image)
    event = Event(
        **event_data.model_dump(), 
        prediction = predict,      
        creator_id=creator_id       
    )
    try:
        statement = select(Wallet).where(Wallet.user_id == creator_id)
        wallet = session.exec(statement).one()  

        transaction = Transaction(
            user_id=creator_id,
            txn_type='Service',
            amount=Decimal("0.01") 
        )
        transaction.execute(wallet)
        session.add_all([transaction, event, wallet])
        session.commit()
        session.refresh(event, attribute_names=["prediction", "creator_id", "creator"])
        return event
    except Exception as e:
        session.rollback()
        raise
"""

def create_event(image: str, creator_id: int, 
                session: Session) -> Event:
    """
    Create new event.
    
    Args:
        event_data: Input data for event
        session: Database session
    
    Returns:
        Event: Created event with ID
    """
  #  predict = model.predict(input_data = event_data.image)
    event = Event(
        title = 'Upload image to predict',     
        image = image,
        description = 'Upload image to predict',
        creator_id=creator_id,
        status = 'Image uploaded'       
    )
    try:
        statement = select(Wallet).where(Wallet.user_id == creator_id)
        wallet = session.exec(statement).one()  

        transaction = Transaction(
            user_id=creator_id,
            txn_type='Service',
            amount=Decimal("0.01") 
        )
        transaction.execute(wallet)
        session.add_all([transaction, event, wallet])
        session.commit()
        session.refresh(event, attribute_names=["prediction", "creator_id", "creator"])
        return event
    except Exception as e:
        session.rollback()
        raise


def prediction_update(event_id: int, model_prediction: str, 
                session: Session) -> Event:
    """
    Update prediction with the data from model.
    
    Args:
        event_id: Event ID
        session: Database session
    """
    try:
        statement = select(Event).where(Event.id == event_id)
        event = session.exec(statement).first()  

        event.prediction = model_prediction
        event.status = 'Success'

        session.add(event)
        session.commit()
        session.refresh(event, attribute_names=["prediction", "creator_id", "status"])
        return event
    except Exception as e:
        session.rollback()
        raise
  

def get_prediction_by_id(event_id: int, session: Session) -> Optional[str]:
    """
    Get prediction by ID.
    
    Args:
        event_id: Event ID to find
        session: Database session
    
    """
    try:
        statement = select(Event).where(Event.id == event_id)
        event = session.exec(statement).first()
        if event is None:
            return None
        return event.prediction
    except Exception as e:
        raise

def delete_all_events(session: Session) -> int:
    """
    Delete all events.
    
    Args:
        session: Database session
    
    Returns:
        int: Number of deleted events
    """
    try:
        statement = select(Event)
        events = session.exec(statement).all()
        count = len(events)
        
        for event in events:
            session.delete(event)
        
        session.commit()
        return count
    except Exception as e:
        session.rollback()
        raise
    
def delete_event(event_id: int, session: Session) -> bool:
    """
    Delete event by ID.
    
    Args:
        event_id: Event ID to delete
        session: Database session
    
    Returns:
        bool: True if deleted, False if not found
    """
    try:
        event = get_event_by_id(event_id, session)
        if not event:
            return False
            
        session.delete(event)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise

