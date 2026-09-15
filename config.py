import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID  = int(os.getenv("OWNER_ID", "0"))

# فقط مالک می‌تونه استفاده کنه
ALLOWED_USERS = [OWNER_ID]

DATA_DIR = "data"
DB_PATH  = f"{DATA_DIR}/data.db"
LOG_PATH = f"{DATA_DIR}/logs.db"

os.makedirs(DATA_DIR, exist_ok=True)
