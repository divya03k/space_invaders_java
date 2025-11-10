# config_tidb.py
import os
from dotenv import load_dotenv

load_dotenv()

TIDB_CONFIG = {
    "host": os.getenv("TIDB_HOST"),
    "port": int(os.getenv("TIDB_PORT", 4000)),
    "user": os.getenv("TIDB_USER"),
    "password": os.getenv("TIDB_PASSWORD"),
    "database": os.getenv("TIDB_DATABASE"),
    "ssl_ca": os.getenv("TIDB_SSL_CA"),
}
API_SERVER = os.getenv("API_SERVER", "http://localhost:5000")
