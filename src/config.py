import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Langfuse
    LANGFUSE_HOST = os.getenv(
        "LANGFUSE_BASE_URL", os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    )
    LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
    LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")

    # LM Studio
    LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")

    # Fireworks AI
    FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY")
    FIREWORKS_BASE_URL = os.getenv(
        "FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1"
    )

    # Model
    MODEL_NAME = os.getenv("MODEL_NAME", "local-model")

    # Use Fireworks if API key is set
    USE_FIREWORKS = bool(FIREWORKS_API_KEY)

    # Evaluation
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", 10))
    NUM_WORKERS = int(os.getenv("NUM_WORKERS", 2))

    # AraTrust
    DATASET_NAME = "asas-ai/AraTrust"
