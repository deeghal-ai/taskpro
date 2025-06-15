# pms/settings/local_postgres.py
# Use this for testing PostgreSQL locally before production deployment
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Local PostgreSQL database (install PostgreSQL locally to test)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'taskpro_local',
        'USER': 'taskpro_user',  # Create this user in your local PostgreSQL
        'PASSWORD': 'your_local_password',  # Set your local password
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend' 