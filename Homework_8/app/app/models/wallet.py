from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal
import re
from models.user import User

class Wallet(SQLModel, table=True):
    """
    Wallet
    
    Attributes:
        user_id (int): Foreign key
        balance (Decimal): Balance
    """
    user_id: int = Field(
        primary_key=True, 
        foreign_key="user.id"
    )
    balance: Decimal = Field(default=Decimal("0.00"))


    @property
    def balance_amount(self) -> Decimal:
        return self.balance
        
      
    