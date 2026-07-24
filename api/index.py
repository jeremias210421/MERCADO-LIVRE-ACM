import sys
import os

# Adicionar o diretório raiz ao path para importar app.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Handler para Vercel
handler = app
