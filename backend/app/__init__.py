# Backend application package
#
# Loads environment variables from backend/.env (if present) BEFORE any
# submodule reads os.environ (database.py reads DATABASE_URL on import, and
# the services read the API keys when they are instantiated).
#
# In production the .env file usually does not exist: load_dotenv() does
# nothing and the backend uses the real environment variables injected by the
# platform. The same code works for both local and production.

from pathlib import Path

from dotenv import load_dotenv

# backend/.env  →  the parent of app/ is the backend/ folder
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)
