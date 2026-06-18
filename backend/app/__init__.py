# Backend application package
#
# Carga las variables de entorno desde backend/.env (si existe) ANTES de que
# cualquier submódulo lea os.environ (database.py lee DATABASE_URL al importarse,
# y los servicios leen las API keys al instanciarse).
#
# En producción el archivo .env normalmente no existe: load_dotenv() no hace
# nada y el backend usa las variables de entorno reales que inyecte la
# plataforma. El mismo código sirve para local y para producción.

from pathlib import Path

from dotenv import load_dotenv

# backend/.env  →  parent de app/ es la carpeta backend/
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)
