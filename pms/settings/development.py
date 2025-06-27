from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Database for development (SQLite)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Email backend for development - CONFIGURED FOR REAL EMAIL SENDING
# Option 1: Console backend (shows emails in terminal)
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Option 2: Real email sending (ACTIVE)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'deeghal.bhaumik@housing.com'
EMAIL_HOST_PASSWORD = 'jfwy dnnj nxnx ceol'

# Email settings
DEFAULT_FROM_EMAIL = 'TaskPro <deeghal.bhaumik@housing.com>' 