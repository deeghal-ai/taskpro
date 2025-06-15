# Development Environment Setup - TaskPro

## ✅ FIXED: Virtual Environment Issue

The error you encountered was because you were running Django from the base anaconda environment instead of your project's virtual environment where the dependencies are installed.

## 📋 Current Setup

- **Virtual Environment**: Pipenv (automatically created)
- **Dependencies**: Installed via pipenv from requirements.txt
- **Database**: SQLite (development)
- **Settings**: `pms.settings.development`

## 🚀 How to Start Development

### Every time you want to work on the project:

1. **Navigate to your project directory:**
   ```bash
   cd C:\Users\Deeghal Bhaumik\Documents\Taskpro\taskpro-fresh
   ```

2. **Activate virtual environment:**
   ```bash
   pipenv shell
   ```

3. **Run Django server:**
   ```bash
   python manage.py runserver
   ```

## 🔧 Common Commands

### Inside Virtual Environment:
```bash
# Run development server
python manage.py runserver

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Django shell
python manage.py shell

# Check for issues
python manage.py check
```

### Managing Dependencies:
```bash
# Install new package
pipenv install package_name

# Install dev dependencies
pipenv install package_name --dev

# Update Pipfile.lock
pipenv lock

# Show dependency graph
pipenv graph
```

## 📁 Project Structure

```
taskpro-fresh/
├── pms/
│   ├── settings/
│   │   ├── base.py          # Common settings
│   │   ├── development.py   # Local development (SQLite)
│   │   ├── production.py    # PythonAnywhere (PostgreSQL)
│   │   └── local_postgres.py # Local PostgreSQL testing
│   └── wsgi.py
├── manage.py
├── requirements.txt         # Dependencies
├── Pipfile                 # Pipenv configuration
├── full_backup.json        # Data backup
└── db.sqlite3             # Development database
```

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'decouple'"
- **Solution**: Make sure you're in the virtual environment (`pipenv shell`)

### "ImportError: Couldn't import Django"
- **Solution**: Activate virtual environment and check if Django is installed

### Database errors:
- **Solution**: Run `python manage.py migrate`

### Static files not loading:
- **Solution**: Run `python manage.py collectstatic`

## 🌟 Best Practices

1. **Always activate virtual environment** before running Django commands
2. **Keep requirements.txt updated** when adding new packages
3. **Test locally** before deploying to production
4. **Use development settings** for local work
5. **Keep your backup files safe** (`full_backup.json`)

## 🚀 Ready for Production

When you're ready to deploy to PythonAnywhere:
1. Follow `DEPLOYMENT_GUIDE.md`
2. Use `QUICK_MIGRATION_STEPS.md` for reference
3. Your production settings are already configured!

---

**Note**: Your development environment is now properly set up and isolated. You can continue working on your TaskPro application without any issues! 