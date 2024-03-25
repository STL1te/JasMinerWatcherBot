import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
BOT_OWNER_ID = int(os.environ.get('BOT_OWNER_ID', 0))

DB_PATH = './shared/database.db'
MINER_DATA_PATH = './shared/miner_data.json'

DEVICES_PER_PAGE = 5
