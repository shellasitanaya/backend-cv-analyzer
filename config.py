import os
from dotenv import load_dotenv

load_dotenv() # Memuat variabel dari file .env

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'kunci-rahasia-default-yang-aman')
    DB_HOST = os.getenv('DB_HOST')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_NAME = os.getenv('DB_NAME')