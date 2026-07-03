from fastapi import APIRouter, Body, HTTPException, status, Depends
from database.database import get_session
from models.transaction import Transaction 
from services.crud import transaction as TransactionService
from typing import List
import logging

# Configure logging
logger = logging.getLogger(__name__)

transaction_router = APIRouter()

@transaction_router.get(
    "/", 
    response_model=List[Transaction],
    summary = "Get all transactions",
    response_description="List of all transactions"
    ) 
async def get_all_transactions(session=Depends(get_session)) -> List[Transaction]:
    """
    Get list of all transactions.

    Args:
        session: Database session

    Returns:
        List[TransactionResponse]: List of transactions
    """
    try:
        transactions = TransactionService.get_all_transactions(session)
        logger.info(f"Retrieved {len(transactions)} transactions")
        return transactions
    except Exception as e:
        logger.info(f"Error retrieving transactions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving transactions"
        )    


@transaction_router.get("/{id}", response_model=Transaction) 
async def retrieve_transaction(id: int, session=Depends(get_session)) -> Transaction:
    try:
        transaction = TransactionService.get_transaction_by_id(id, session)
    except Exception as e:
        logger.error(f"Database error: {str(e)}")   
    if transaction is None:
        logger.warning(f"Transaction with id {id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Transaction with supplied ID does not exist"
        )

    logger.info(f"Retrieved transaction {id}")
    return transaction

 

@transaction_router.get("/user/{user_id}", response_model=List[Transaction]) 
async def retrieve_transaction_by_user_id(user_id: int, session=Depends(get_session)) -> List[Transaction]:
    try:
        transactions = TransactionService.get_transaction_by_user_id(user_id, session)
    except Exception as e:
        logger.error(f"Database error: {str(e)}")   
    if not transactions:
        logger.warning(f"Transactions for user {user_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Transactions for supplied user_ID don't exist"
        )
    logger.info(f"Retrieved transactions for user {user_id}")
    return transactions   

"""
@transaction_router.delete("/{id}")
async def delete_transaction(id: int) -> dict: 
    for transaction in tansactions:
        if transaction.id == id: 
            transactions.remove(tansaction)
            return {"message": "Transaction deleted successfully"}
        raise HTTPException(status_code=status. HTTP_404_NOT_FOUND, 
        detail="Transaction with supplied ID does not exist")

@transaction_router.delete("/")
async def delete_all_transactions() -> dict: 
    transactions.clear()
    return {"message": "Transactions deleted successfully"}
"""