from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from models.user import User

class EventBase(SQLModel):
    """
    Base Event model with common fields.
    
    Attributes:
        text (str): Review text
    """
    text: str = Field(..., min_length=3, max_length=2000)


class Event(EventBase, table=True):
    """
    Event model representing events in the system.
    
    Attributes:
        id (Optional[int]): Primary key
        creator_id (Optional[int]): Foreign key to User
        creator (Optional[User]): Relationship to User
        prediction(str): Model's prediction class for the image
        created_at (datetime): Event creation timestamp
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    creator_id: Optional[int] = Field(default=None, foreign_key="user.id")
    creator: Optional["User"] = Relationship(
        back_populates="events",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    object_id: Optional[int] = Field(default=None, foreign_key="object.id") 
    status: str =  Field(..., min_length=1, max_length=100)
    prediction: Optional[int] = Field(default=None)
    confidence: Optional[float] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def __str__(self) -> str:
        result = (f"Id: {self.id}. Short text: {self.short_text}. Creator id: {self.creator_id}")
        return result

    @property
    def short_text(self) -> str:
        max_length = 50
        return f"{self.text[:max_length]}..." if len(self.text) > max_length else self.text   

class EventCreate(EventBase):
    """Schema for creating new events"""
    pass

class EventUpdate(EventBase):
    """Schema for updating existing events"""    
    status: Optional[str] = None
    prediction: Optional[str] = None
    confidence: Optional[float] = None

    class Config:
        """Model configuration"""
        validate_assignment = True

