import os
from pathlib import Path

class Config:
    SECRET_KEY = 'Secret_key'
    UPLOAD_FOLDER = Path('uploads')
    OUTPUT_FOLDER = Path('output')
    MAX_CONTENT_LENGHT = 16 * 1024 * 1024
