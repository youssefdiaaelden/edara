from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATABASE_PATH = BASE_DIR / "database" / "store.db"

ASSETS_PATH = BASE_DIR / "assets"

FONT_PATH = ASSETS_PATH / "fonts" / "Amiri-Regular.ttf"

RECEIPTS_PATH = BASE_DIR / "receipts"

BACKUPS_PATH = BASE_DIR / "backups"

LOGS_PATH = BASE_DIR / "logs"

MODELS_PATH = BASE_DIR / "ai" / "models"

DATASETS_PATH = BASE_DIR / "ai" / "datasets"

HOST = "127.0.0.1"

PORT = 5000

DEBUG = True
