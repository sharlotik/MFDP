from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal
import re
from models.user import User

class Transaction(SQLModel, table=True): 
    """
    Transactions
    
    Attributes:
        id (int): Primary key
        user_id (int): Foreign key
        txn_type (str): Transaction type
        amount (Decimal): Transaction amount
        description (str): Transaction description
        report_dttm: datetime Transaction datetime
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    txn_type: str
    amount: Decimal
    report_dttm: datetime = Field(default_factory=datetime.utcnow)

    def execute(self, wallet: 'Wallet'):
        if self.txn_type == 'Deposit':
            wallet.balance += self.amount
            
        elif self.txn_type == 'Service':
            if wallet.balance < self.amount:
                raise ValueError("Insufficient funds")
            wallet.balance -= self.amount
