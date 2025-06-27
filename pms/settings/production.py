from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

# Add your PythonAnywhere domain here
ALLOWED_HOSTS = [
    config('ALLOWED_HOST', default='deeghalbhaumik.pythonanywhere.com'),
    'taskspro.in',
    'www.taskspro.in',
    'localhost',
    '127.0.0.1',
]

# Database for production (MySQL - Free on PythonAnywhere)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='deeghalbhaumik.mysql.pythonanywhere-services.com'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': {
            'sql_mode': 'traditional',
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Security settings for production - TEMPORARILY DISABLED FOR DEBUGGING
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_SECONDS = 0
SECURE_REDIRECT_EXEMPT = []
SECURE_SSL_REDIRECT = False
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # Disabled

# CSRF settings
CSRF_COOKIE_SECURE = False  # Disable for HTTP domains
CSRF_TRUSTED_ORIGINS = [
    'https://' + config('ALLOWED_HOST', default='deeghalbhaumik.pythonanywhere.com'),
    'http://taskspro.in',
    'http://www.taskspro.in',
    'https://taskspro.in',
    'https://www.taskspro.in',
]

# Session settings
SESSION_COOKIE_SECURE = False  # Disable for HTTP domains
SESSION_COOKIE_HTTPONLY = True

# Email settings (with fallback to your Gmail credentials)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='deeghal.bhaumik@housing.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='jfwy dnnj nxnx ceol')

# Email timeout and retry settings for production
EMAIL_TIMEOUT = 30
EMAIL_CONNECTION_RETRY_DELAY = 1

# Override base settings for production
DEFAULT_FROM_EMAIL = f'TaskPro <{EMAIL_HOST_USER}>'
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Improved email error handling
EMAIL_SUBJECT_PREFIX = '[TaskPro] '

# Logging for production - Inherits from base.py
# The LOGS_DIR created in base.py will be used automatically.
# No need to override the filename here.