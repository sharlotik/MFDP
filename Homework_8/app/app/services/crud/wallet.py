from models.event import Event, EventUpdate
from sqlmodel import Session, select
from sqlalchemy.orm import load_only 
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from models.wallet import Wallet

### Wallet создается одновременно с User

def get_balance_by_user_id(user_id: int, session: Session) -> Optional[Decimal]:
    """
    Get balance by user ID.
    
    Args:
        user_id: User ID to find
        session: Database session
    
    Returns:
        Optional[Event]: Found balance or None
    """
    try:
        statement = select(Wallet).where(Wallet.user_id == user_id).options(
            load_only(Wallet.balance)
        )
        wallet = session.exec(statement).first()
        return wallet.balance if wallet else None
    except Exception as e:
        raise

