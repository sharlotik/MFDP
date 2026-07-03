from models.event import Event, EventUpdate
from models.transaction import Transaction
from sqlmodel import Session, select
from sqlalchemy.orm import load_only 
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from models.wallet import Wallet

def get_all_transactions(session: Session) -> List[Transaction]:
    """
    Retrieve all Transaction.
    
    Args:
        session: Database session
    
    Returns:
        List[Transaction]: List of all transactions
    """
    try:
        statement = select(Transaction)
        transactions = session.exec(statement).all()
        return transactions
    except Exception as e:
        raise


def get_transaction_by_id(transaction_id: int, session: Session) -> Optional[Transaction]:
    """
    Get transaction by ID.
    
    Args:
        transaction_id: Transaction ID to find
        session: Database session
    
    Returns:
        Optional[Transaction]: Found transaction or None
    """
    try:
        statement = select(Transaction).where(Transaction.id == transaction_id)
        transaction = session.exec(statement).first()
        return transaction
    except Exception as e:
        raise

def get_transaction_by_user_id(user_id: int, session: Session) -> List[Transaction]:
    """
    Get transaction by user_id.
    
    Args:
        user_id: user_id to find
        session: Database session
    
    Returns:
        Optional[Transaction]: Found transaction or None
    """
    try:
        statement = select(Transaction).where(Transaction.user_id == user_id)
        transaction = session.exec(statement).all()
        return transaction
    except Exception as e:
        raise        


def create_transaction(user_id: int, txn_type : str, amount : Decimal, 
                        session: Session) -> Transaction:
    """
    Create new transaction.
    
    Args:
        session: Database session
    
    Returns:
        Transaction: Created transaction with ID
    
    """
    amount = Decimal(str(amount))

    if txn_type == 'Deposit':
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        description = 'Пополнение баланса'
            
    elif txn_type == 'Service':
        statement = select(Wallet).where(Wallet.user_id == user_id)
        amount = Decimal("0.01") 
        wallet = session.exec(statement).one()
        if wallet.balance < amount:
            raise ValueError("Service amount must be less than balance")
        description = 'Вызов модели'
                    
    transaction = Transaction(
        user_id = user_id, 
        txn_type = txn_type,      
        amount =  amount,
        description = description       
    )

    statement = select(Wallet).where(Wallet.user_id == user_id)
    wallet = session.exec(statement).one()
        
    transaction.execute(wallet)
    
    try:
        session.add(transaction)
        session.add(wallet)
        session.commit()
        session.refresh(transaction)
        return transaction
    except Exception as e:
        session.rollback()
        print(f"ОШИБКА БАЗЫ ДАННЫХ: {e}")
        raise
  