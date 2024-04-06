from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.auth.router import router as auth_router
from src.config import app_configs, settings
from src.database import Database
from src.nlp.config import nlp_config
from src.nlp.models import load_bertopic_model, load_embeddings_model
from src.nlp.router import router as nlp_router


# Define an async context manager for the lifespan of the FastAPI application
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    try:
        # Startup
        await Database.connect(settings.DATABASE_URL, settings.DATABASE_NAME)
        model_object_name = nlp_config.MODEL_NAME
        app.state.bertopic_model = await load_bertopic_model(model_object_name)
        print("BERTopic model loaded successfully. ")
        app.state.tokenizer, app.state.model = await load_embeddings_model()
        print("Embeddings model loaded successfully.")
        yield
    except Exception as e:
        print(f"Failed to start the application: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Shutdown
        try:
            Database.close()
            print("Database connection closed.")
        except Exception as e:
            print(f"Failed to close the database connection: {e}")
            import traceback

            traceback.print_exc()


def setup_logging():
    logging_format = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
    logging_level = (
        logging.DEBUG if os.getenv("ENVIRONMENT") == "development" else logging.INFO
    )
    logging.basicConfig(format=logging_format, level=logging_level)


setup_logging()
logger = logging.getLogger(__name__)

# Create a FastAPI application instance with the specified configurations and lifespan
app = FastAPI(**app_configs, lifespan=lifespan)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGINS_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=settings.CORS_HEADERS,
)


# Define the root endpoint
@app.get("/")
async def root():
    """
    Root endpoint of the FastAPI application.
    Returns a welcome message.
    """
    return {"message": "Welcome to my FastAPI application!"}


# Define the healthcheck endpoint
@app.get("/healthcheck", include_in_schema=False)
async def healthcheck() -> dict[str, str]:
    """
    Healthcheck endpoint of the FastAPI application.
    Returns the status of the application.
    """
    return {"status": "ok"}


# Include the auth router with the specified prefix and tags
app.include_router(auth_router, prefix="/auth", tags=["Auth"])

# Include the NLP router with the specified prefix and tags
app.include_router(nlp_router, prefix="/nlp", tags=["NLP"])
