from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from models.user import User
    from models.event import Event

class ObjectBase(SQLModel):
    name: str = Field(..., min_length=2, max_length=150)
    address: str = Field(..., min_length=5, max_length=255)
    place_id: Optional[str] = Field(default=None)


class Object(ObjectBase, table=True):


    id: Optional[int] = Field(default=None, primary_key=True)   
    user_id: int = Field(foreign_key="user.id")    
    events: List["Event"] = Relationship(
        back_populates="object_rel", 
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan", 
            "lazy": "selectin"
        }
    )

    def __str__(self) -> str:
        return f"Object ID: {self.id} | Name: {self.name} | Address: {self.address}"


class ObjectCreate(ObjectBase):
    user_id: int


class ObjectUpdate(SQLModel):
    name: Optional[str] = None
    address: Optional[str] = None
    place_id: Optional[str] = None