from fastapi import APIRouter, HTTPException, status, Depends
from database.database import get_session
from pydantic import BaseModel, Field#, EmailStr
from models.user import User
from services.crud import user as UserService
from sqlmodel import Session  
from models.wallet import Wallet  
from services.crud import object as ObjectService
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

user_route = APIRouter()

class UserSignupRequest(BaseModel):
    email: str = Field(..., description="User email address") #EmailStr
    password: str = Field(..., min_length=4)
    object_id: int = Field(..., description="ID компании, к которой привязан пользователь")

class UserSigninRequest(BaseModel):
    email: str#EmailStr
    password: str


@user_route.post(
    '/signup',
    response_model=Dict[str, str],
    status_code=status.HTTP_201_CREATED,
    summary="User Registration",
    description="Register a new user and bind them to an existing Object ID"
)
async def signup(data: UserSignupRequest, session: Session = Depends(get_session)) -> Dict[str, str]:
    try:
        company = ObjectService.get_object_by_id(data.object_id, session)
        if not company:
            logger.warning(f"Signup tools: Object ID {data.object_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ID {data.object_id} does not exist. Create the company first."
            )

        if UserService.get_user_by_email(data.email, session):
            logger.warning(f"Signup attempt with existing email: {data.email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )

        user = User(
            email=data.email,
            password=data.password, 
            object_id=data.object_id,
            company_name=None 
        )
        session.add(user)
        session.flush() 

        wallet = Wallet(user_id=user.id, balance="0.00")
        session.add(wallet)

        session.commit()
        
        logger.info(f"New user registered: {data.email} for Object ID: {data.object_id}")
        return {"message": "User successfully registered and linked to the company"}

    except HTTPException:
        session.rollback()
        raise

    except Exception as e:
        session.rollback()
        logger.error(f"Error during signup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}" 
        )

@user_route.post('/signin')
async def signin(data: UserSigninRequest, session: Session = Depends(get_session)) -> Dict[str, str]:
    """
    Authenticate existing user.
    """
    try:
        user = UserService.get_user_by_email(data.email, session)
        if user is None:
            logger.warning(f"Login attempt with non-existent email: {data.email}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")
        
        if user.password != data.password:
            logger.warning(f"Failed login attempt for user: {data.email}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wrong credentials passed")
        
        return {"message": "User signed in successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during signin logic: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error"
        )

@user_route.get(
    "/",
    response_model=List[User],
    summary="Get all users",
    response_description="List of all users"
)
async def get_all_users(session: Session = Depends(get_session)) -> List[User]:
    try:
        users = UserService.get_all_users(session)
        logger.info(f"Retrieved {len(users)} users")
        return users
    except Exception as e:
        logger.error(f"Error retrieving users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving users"
        )


@user_route.get("/user/{user_id}", response_model=User) 
async def get_user_by_id(user_id: int, session: Session = Depends(get_session)) -> User:
    try:
        user = UserService.get_user_by_id(user_id, session)
        # Fixed: Moved validation inside try block to shield from UnboundLocalError database faults
        if not user:
            logger.warning(f"User {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="User_ID doesn't exist"
            )
        logger.info(f"Retrieved user {user_id}")
        return user   
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error during ID lookup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error"
        )

@user_route.get("/email/{email}", response_model=User) 
async def get_user_by_email(email: str, session: Session = Depends(get_session)) -> User:
    try:
        user = UserService.get_user_by_email(email, session)
        # Fixed: Moved validation inside try block to shield from UnboundLocalError database faults
        if not user:
            logger.warning(f"User with email {email} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="User with this email doesn't exist"
            )
        logger.info(f"Retrieved user with email {email}")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error during email lookup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error"
        )