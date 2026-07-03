from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.home import home_route
from routes.auth import auth_route
from routes.user import user_route
from routes.event import event_router
from routes.transaction import transaction_router
from routes.wallet import wallet_router
#from routes.model import model_router
from database.database import init_db
from database.config import get_settings
import uvicorn
import logging
from fastapi.staticfiles import StaticFiles
import os


logger = logging.getLogger(__name__)
settings = get_settings()
app = FastAPI() 
app.mount("/uploads", StaticFiles(directory="../data/images"), name="uploads")

def create_application() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    """
    
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.API_VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    app.include_router(home_route, tags=['Home'])
    app.include_router(auth_route, prefix='/auth', tags=['Auth'])
    app.include_router(user_route, prefix='/api/users', tags=['Users'])
    app.include_router(event_router, prefix='/api/events', tags=['Events'])
    app.include_router(transaction_router, prefix='/api/transactions', tags=['Transactions'])
    app.include_router(wallet_router, prefix='/api/wallets', tags=['Wallets'])
    #app.include_router(prediction_router, prefix='/api/predictions', tags=['Predictions'])

    return app

app = create_application()

@app.get("/test") # название ресурса
def test():
    return {"message": "Hello World!"}

@app.on_event("startup") 
def on_startup():
    try:
        logger.info("Initializing database...")
        init_db()
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise
    
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Application shutting down...")

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    uvicorn.run(
        'api:app',
        host='0.0.0.0',
        port=8080,
        reload=True,
        log_level="info"
    )