from fastapi import APIRouter, HTTPException, status, Depends
from database.database import get_session
from models.object import Object, ObjectBase 
from services.crud import object as ObjectService
from services.crud import user as UserService  
from typing import List
import logging

logger = logging.getLogger(__name__)

object_router = APIRouter(prefix="/objects", tags=["Objects"])

@object_router.post(
    "/", 
    response_model=Object, 
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Object (Company)",
    description="Register a new business object (restaurant, cafe, hotel) in the system."
)
async def create_new_object(data: ObjectBase, session=Depends(get_session)) -> Object:
    try:
        db_object = Object(
            name=data.name,
            address=data.address,
            category=data.category,
            place_id=data.place_id
        )
        
        created_object = ObjectService.create_object(db_object, session)
        logger.info(f"New object created successfully: {created_object.name} (ID: {created_object.id})")
        return created_object

    except Exception as e:
        logger.error(f"Error creating business object record: {str(e)}")
        if "unique" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A company with this unique specification or name already exists."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while creating the object."
        )



@object_router.get(
    "/", 
    response_model=List[Object],
    summary="Get all Objects",
    response_description="List of all objects"
) 
async def get_all_objects(session=Depends(get_session)) -> List[Object]:
    """
    Retrieve all registered business objects (restaurants, cafes, hotels).
    """
    try:
        objects = ObjectService.get_all_objects(session)
        logger.info(f"Retrieved {len(objects)} objects")
        return objects
    except Exception as e:
        logger.error(f"Error retrieving objects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving objects from database"
        )    


@object_router.get(
    "/{id}", 
    response_model=Object,
    summary="Get object by ID"
) 
async def retrieve_object(id: int, session=Depends(get_session)) -> Object:
    """
    Retrieve a specific business object by its unique ID.
    """
    try:
        db_object = ObjectService.get_object_by_id(id, session)
        if db_object is None:
            logger.warning(f"Object with id {id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Object with supplied ID does not exist"
            )
        logger.info(f"Retrieved object {id}")
        return db_object
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error during object ID lookup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )


@object_router.get(
    "/user/{user_id}", 
    response_model=Object,
    summary="Get object by User ID"
) 
async def retrieve_object_by_user_id(user_id: int, session=Depends(get_session)) -> Object:
    """
    Retrieve the assigned business object for a specific manager user ID.
    """
    try:
        user = UserService.get_user_by_id(user_id, session)
        if not user:
            logger.warning(f"User with ID {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with supplied ID does not exist"
            )

        if user.object_id is None:
            logger.warning(f"User with ID {user_id} is not assigned to any business object")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="This user account is not linked to any business object"
            )

        db_object = ObjectService.get_object_by_id(user.object_id, session)
        if not db_object:
            logger.warning(f"Object ID {user.object_id} linked to user {user_id} does not exist in DB")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="The linked business object could not be found"
            )
            
        logger.info(f"Retrieved object {db_object.id} for user {user_id}")
        return db_object

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error during user-to-object mapping: {str(e)}")   
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )