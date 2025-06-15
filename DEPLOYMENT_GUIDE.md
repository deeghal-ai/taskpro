# TaskPro Deployment Guide - MySQL Migration & PythonAnywhere

This guide will help you migrate from SQLite to MySQL and deploy your application on PythonAnywhere.

## Pre-Deployment Checklist

### 1. Backup Your Data
✅ Data backup created: `full_backup.json`

### 2. Install Dependencies Locally
```bash
pip install -r requirements.txt
```

### 3. Test Locally (Optional but Recommended)
Before deploying to production, you can test MySQL locally:

1. Install MySQL on your local machine
2. Create a database and user:
   ```sql
   CREATE DATABASE taskpro_local;
   CREATE USER 'taskpro_user'@'localhost' IDENTIFIED BY 'your_local_password';
   GRANT ALL PRIVILEGES ON taskpro_local.* TO 'taskpro_user'@'localhost';
   FLUSH PRIVILEGES;
   ```
3. Test migration:
   ```bash
   python manage.py migrate --settings=pms.settings.production
   python manage.py loaddata full_backup.json --settings=pms.settings.production
   python manage.py runserver --settings=pms.settings.production
   ```

## PythonAnywhere Deployment Steps

### Step 1: Upload Your Code
1. Create a PythonAnywhere account
2. Upload your project files to PythonAnywhere or clone from Git:
   ```bash
   git clone <your-repo-url>
   cd taskpro-fresh
   ```

### Step 2: Create Virtual Environment
```bash
cd ~
python3.10 -m venv venv
source venv/bin/activate
cd ~/taskpro-fresh
pip install -r requirements.txt
```

### Step 3: Set Up MySQL Database
1. Go to PythonAnywhere Dashboard > Databases
2. Create a new MySQL database (FREE)
3. Note down:
   - Database name: `yourusername$taskpro`
   - Username: `yourusername`
   - Password: (the one you set)
   - Host: `yourusername.mysql.pythonanywhere-services.com`

### Step 4: Create Environment Variables
Create a `.env` file in your project root:
```bash
# Copy from env_template.txt and fill in actual values:
SECRET_KEY=generate-a-new-secret-key
DEBUG=False
DJANGO_SETTINGS_MODULE=pms.settings.production

# Replace with your actual PythonAnywhere domain
ALLOWED_HOST=yourusername.pythonanywhere.com

# Database settings from PythonAnywhere
DB_NAME=yourusername$taskpro
DB_USER=yourusername
DB_PASSWORD=your_database_password
DB_HOST=yourusername.mysql.pythonanywhere-services.com
DB_PORT=3306
```

### Step 5: Run Migrations
```bash
python manage.py migrate --settings=pms.settings.production
```

### Step 6: Load Your Data
```bash
python manage.py loaddata full_backup.json --settings=pms.settings.production
```

### Step 7: Collect Static Files
```bash
python manage.py collectstatic --settings=pms.settings.production
```

### Step 8: Create Superuser (if needed)
```bash
python manage.py createsuperuser --settings=pms.settings.production
```

### Step 9: Configure WSGI
1. Go to PythonAnywhere Dashboard > Web
2. Create a new web app (manual configuration)
3. Set the WSGI configuration file path: `/home/yourusername/taskpro-fresh/pms/wsgi.py`
4. Update WSGI file to ensure it uses production settings (already configured)

### Step 10: Set Up Static Files
In the PythonAnywhere web tab:
- Static URL: `/static/`
- Static directory: `/home/yourusername/taskpro-fresh/staticfiles/`

### Step 11: Environment Variables in WSGI
Edit your WSGI file to load environment variables:
```python
import os
import sys
from decouple import config

# Add your project directory to sys.path
path = '/home/yourusername/taskpro-fresh'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'pms.settings.production'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

## Important Security Notes

1. **Never commit your .env file** - Add it to .gitignore
2. **Generate a new SECRET_KEY** for production
3. **Use strong database passwords**
4. **Keep DEBUG=False** in production
5. **Update ALLOWED_HOSTS** with your actual domain

## Testing Your Deployment

1. Visit your PythonAnywhere URL
2. Test login functionality
3. Check admin panel access
4. Verify all features work correctly
5. Monitor the error log for any issues

## Troubleshooting

### Common Issues:

1. **Import Errors**: Check your Python path in WSGI file
2. **Database Connection**: Verify database credentials in .env
3. **Static Files**: Ensure STATIC_ROOT and WhiteNoise are configured
4. **CSRF Errors**: Check CSRF_TRUSTED_ORIGINS setting
5. **SSL Issues**: Ensure SECURE_SSL_REDIRECT is properly configured

### Logs Location:
- Error logs: PythonAnywhere Dashboard > Tasks & consoles > Error log
- Application logs: Check the logs directory

## Rollback Plan

If something goes wrong:
1. Switch back to development settings locally
2. Use the SQLite backup to restore data
3. Debug issues before attempting deployment again

## Contact Information

For issues specific to this deployment, check:
- Django documentation
- PythonAnywhere help pages
- PostgreSQL documentation 