import os
import sys
from dotenv import load_dotenv

# Forçar UTF-8 no Windows — resolve UnicodeDecodeError do .env
if sys.platform == 'win32':
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

# Carregar .env com encoding UTF-8 explícito
load_dotenv(encoding='utf-8')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'neurolink2025spynet')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False  # Desativado para simplificar desenvolvimento
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
    ZAPI_INSTANCE_ID  = os.environ.get('ZAPI_INSTANCE_ID', '')
    ZAPI_TOKEN        = os.environ.get('ZAPI_TOKEN', '')
    ZAPI_BASE_URL     = os.environ.get('ZAPI_BASE_URL', '')
    GOOGLE_MAPS_KEY   = os.environ.get('GOOGLE_MAPS_KEY', '')
    PAYMENT_API_KEY   = os.environ.get('PAYMENT_API_KEY', '')


class DevelopmentConfig(Config):
    DEBUG = True
    # Sempre usar SQLite — sem problemas de encoding de senha
    SQLALCHEMY_DATABASE_URI = 'sqlite:///neurolink_tea.db'
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///neurolink_tea.db'
    ).replace('postgres://', 'postgresql://')
    SESSION_COOKIE_SECURE   = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'testing':     TestingConfig,
    'default':     DevelopmentConfig,
}
