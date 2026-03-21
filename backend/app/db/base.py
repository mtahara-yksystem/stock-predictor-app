# backend/app/db/base.py
import os

from sqlalchemy import create_engine

# 1. 確実に backend ディレクトリまで遡る
# __file__ は backend/app/db/base.py なので、3回 dirname すると backend/ になる
current_dir = os.path.dirname(os.path.abspath(__file__))  # .../db
app_dir = os.path.dirname(current_dir)  # .../app
project_root = os.path.dirname(app_dir)  # .../backend (ここがルート)

DB_PATH = os.path.join(project_root, "data", "stock_system.db")


class Database:
    def __init__(self):
        self.engine = create_engine(f"sqlite:///{DB_PATH}")
