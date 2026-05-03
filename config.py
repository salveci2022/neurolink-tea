import os
import sys
from dotenv import load_dotenv

if sys.platform == 'win32':
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

load_dotenv(encoding='utf-8')


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'neurolink2025spynet')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
    ZAPI_INSTANCE_ID  = os.environ.get('ZAPI_INSTANCE_ID', '')
    ZAPI_TOKEN        = os.environ.get('ZAPI_TOKEN', '')
    ZAPI_BASE_URL     = os.environ.get('ZAPI_BASE_URL', '')


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///neurolink_tea.db'


class ProductionConfig(Config):
    DEBUG = False
    # Render.com usa DATABASE_URL com postgres:// — corrigir para postgresql://
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///neurolink_tea.db')
    SQLALCHEMY_DATABASE_URI = db_url.replace('postgres://', 'postgresql://')


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
