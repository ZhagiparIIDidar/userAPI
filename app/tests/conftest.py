import sys
import os

# Добавляем родительскую директорию файла conftest.py в sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
