import os
from pathlib import Path
from dotenv import load_dotenv

# Find the project root directory
BASE_DIR = Path(__file__).resolve().parents[2]

# Load environment variables from the root .env file
load_dotenv(BASE_DIR / ".env")

# Groq configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

# Embedding configuration
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Dataset location
DATASET_DIR = BASE_DIR / "veridian_legal_dataset"

# Local Qdrant database location
QDRANT_PATH = BASE_DIR / "qdrant_storage"
