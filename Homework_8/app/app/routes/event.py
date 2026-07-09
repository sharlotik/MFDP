from fastapi import APIRouter, Body, HTTPException, status, Depends
from fastapi import FastAPI, UploadFile, File
from database.database import get_session
from models.event import Event, EventCreate 
from models.model import Model
from services.crud import event as EventService
from pydantic import BaseModel, Field 
from typing import List
import logging
import shutil
import os
import json
import io  
import pandas as pd  
from services.rm import rm as rm_module
from sqlmodel import Session, select 

# Configure logging
logger = logging.getLogger(__name__)

event_router = APIRouter()


class ReviewUploadPayload(BaseModel):
    creator_id: int = Field(..., description="ID of the manager who uploaded the review")
    text: str = Field(..., description="The text of the review")

    class Config:
        json_schema_extra = {
            "example": {
                "creator_id": 1,
                "text": "Отличный сервис, всё очень понравилось! Но пиццу несли долго."
            }
        }

@event_router.get(
    "/", 
    response_model=List[Event],
    summary = "Get all events",
    response_description="List of all events") 
async def get_all_events(session=Depends(get_session)) -> List[Event]:
    """
    Get list of all events.

    Args:
        session: Database session

    Returns:
        List[TransactionResponse]: List of events
    """
    try:
        events = EventService.get_all_events(session)
        logger.info(f"Retrieved {len(events)} events")
        return events
    except Exception as e:
        logger.info(f"Error retrieving events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving events"
        )    


@event_router.get("/{id}", response_model=Event) 
async def retrieve_event(id: int, session=Depends(get_session)) -> Event:
    try:
        event = EventService.get_event_by_id(id, session)
    except Exception as e:
        logger.error(f"Database error: {str(e)}")   
    if event is None:
        logger.warning(f"Event with id {id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Event with supplied ID does not exist"
        )

    logger.info(f"Retrieved event {id}")
    return event


"""
    @event_router.post("/new")
    async def create_event( creator_id: int, model : Model = Depends(get_model),
                            event_data: EventCreate = Body(...),
                            session=Depends(get_session)) -> dict: 
        try:
            EventService.create_event(
            event_data = event_data, 
            creator_id = creator_id,
            model = model,
            session = session)
            return {"message": "Event created successfully"}
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                    detail=f"Internal Server Error {type(e).__name__}: {str(e)}")
"""


@event_router.post("/upload_file/")
async def upload_reviews_via_file(
    creator_id: int,
    file: UploadFile = File(...),
    session = Depends(get_session)
):
    contents = await file.read()
    reviews_list = []

    try:
        if file.filename.endswith('.txt'):
            text_data = contents.decode("utf-8")
            reviews_list = [line.strip() for line in text_data.split('\n') if line.strip()]
        elif file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
            reviews_list = df.iloc[:, 0].dropna().astype(str).tolist()
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(contents))
            reviews_list = df.iloc[:, 0].dropna().astype(str).tolist()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Incorrect file format. Only .txt, .csv, and .xlsx files are allowed"
            )
    except HTTPException:
        raise
    except Exception as parse_err:
        logger.error(f"Error parsing file {file.filename}: {str(parse_err)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Failed to read file structure: {str(parse_err)}"
        )

    if not reviews_list:
        raise HTTPException(status_code=400, detail="The file is empty or contains no valid text lines")

    created_event_ids = []
    try:
        for text in reviews_list:
            if not text.strip():
                continue
                
            new_event = EventService.create_event(
                image=text, 
                creator_id=creator_id,
                session=session
            )
            
            task_worker = {
                "event_id": new_event.id,  
                "text": text  
            }
            rm_module.send_task(json.dumps(task_worker)) 
            created_event_ids.append(new_event.id)
            
        logger.info(f"Successfully processed file {file.filename}. Dispatched {len(created_event_ids)} tasks.")
        return {
            "message": "File successfully accepted and queued for batch processing",
            "filename": file.filename,
            "total_reviews": len(reviews_list),
            "successfully_queued_events": created_event_ids
        }
    except Exception as e:
        logger.error(f"Critical error during batch file processing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Server error while adding the batch payload to the queue: {str(e)}"
        )


@event_router.post("/upload_review/", status_code=status.HTTP_201_CREATED)
async def upload_review(
    payload: ReviewUploadPayload, 
    session = Depends(get_session)
):
    """
    Endpoint for uploading a single Russian review from an input text box.
    """
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Review text cannot be empty")

    try:

        new_event = EventService.create_event(
            image=payload.text, 
            creator_id=payload.creator_id,
            session=session
        )

        task_worker = {
            "event_id": new_event.id,  
            "text": payload.text  
        }
        rm_module.send_task(json.dumps(task_worker)) 
        logger.info(f"Single review task for event {new_event.id} successfully dispatched to worker queue.")
                   
        return {
            "message": "Review uploaded successfully", 
            "event_id": new_event.id,
            "creator_id": payload.creator_id,
            "preview": payload.text[:100] + "..."
        }
    except Exception as e:
        logger.error(f"Error creating review event: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Internal Server Error: {str(e)}"
        )

@event_router.get("/prediction/{id}", summary="Get review analysis status and results")
async def retrieve_prediction(id: int, session: Session = Depends(get_session)):
    """
    Retrieve the current processing status and computed AI prediction for a specific review by its ID.
    """
    try:
        event = EventService.get_event_by_id(id, session)
        
        if event is None:
            logger.warning(f"Event record with ID {id} not found in the architecture")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Review event with the supplied ID does not exist."
            )
            
        logger.info(f"Retrieved operational state for event {id}")
        review_text = getattr(event, 'text', None) or getattr(event, 'image', "Текст отсутствует")
        return {
            "event_id": event.id,
            "current_status": event.status,  
            "review_text": review_text, #event.text,
            "ai_rating": event.prediction if event.prediction is not None else "In progress... Please refresh in a few seconds.",
            "confidence": f"{event.confidence * 100:.2f}%" if event.confidence is not None else "Calculating..."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database fault during prediction payload retrieval: {str(e)}", exc_info=True)   
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error occurred while fetching the analysis state."
        )
'''
@event_router.delete("/{id}")
async def delete_event(id: int) -> dict: 
    for event in events:
        if event.id == id: 
            events.remove(event)
            return {"message": "Event deleted successfully"}
        raise HTTPException(status_code=status. HTTP_404_NOT_FOUND, detail="Event with supplied ID does not exist")

@event_router.delete("/")
async def delete_all_events() -> dict: 
    events.clear()
    return {"message": "Events deleted successfully"}
    '''