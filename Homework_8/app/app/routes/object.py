from fastapi import APIRouter, Body, HTTPException, status, Depends
from database.database import get_session
from models.object import Object 
from services.crud import object as ObjectService
from typing import List
import logging

# Configure logging
logger = logging.getLogger(__name__)

transaction_router = APIRouter()

@object_router.get(
    "/", 
    response_model=List[Object],
    summary = "Get all Objects",
    response_description="List of all objects"
    ) 
async def get_all_objects(session=Depends(get_session)) -> List[Object]:
    """
    Get list of all objects.

    Args:
        session: Database session

    Returns:
        List[ObjectResponse]: List of objects
    """
    try:
        objects = ObjectService.get_all_objects(session)
        logger.info(f"Retrieved {len(objects)} objects")
        return objects
    except Exception as e:
        logger.info(f"Error retrieving objects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving objects"
        )    


@object_router.get("/{id}", response_model=Object) 
async def retrieve_object(id: int, session=Depends(get_session)) -> Object:
    try:
        object = ObjectService.get_object_by_id(id, session)
    except Exception as e:
        logger.error(f"Database error: {str(e)}")   
    if object is None:
        logger.warning(f"Object with id {id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Object with supplied ID does not exist"
        )

    logger.info(f"Retrieved object {id}")
    return object

 

@object_router.get("/user/{user_id}", response_model=List[Object]) 
async def retrieve_object_by_user_id(user_id: int, session=Depends(get_session)) -> List[Object]:
    try:
        objects = ObjectService.get_object_by_user_id(user_id, session)
    except Exception as e:
        logger.error(f"Database error: {str(e)}")   
    if not objects:
        logger.warning(f"Objects for user {user_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Objects for supplied user_ID don't exist"
        )
    logger.info(f"Retrieved objects for user {user_id}")
    return objects   