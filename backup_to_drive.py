#!/usr/bin/env python
"""
Database Backup Script for TaskPro - Single Excel File Version
Exports selected tables as sheets in ONE Excel file and uploads to Google Shared Drive

Author: TaskPro Team
Created for: deeghalbhaumik
Authentication: Service Account (for corporate Google Workspace)
"""
import os
import sys
import django
from datetime import datetime, timedelta
from pathlib import Path

# Setup Django environment
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pms.settings.production')
django.setup()

import pandas as pd
from django.db import connection
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

class DatabaseBackup:
    """
    Handles daily database backups to Google Shared Drive.
    Creates ONE Excel file with all tables as separate sheets.
    """
    
    # Tables to backup - organized by app
    TABLES_TO_BACKUP = [
        # Accounts app (1 table)
        'accounts_user',
        
        # Locations app (2 tables)
        'locations_city',
        'locations_region',
        
        # Projects app (13 tables)
        'projects_project',
        'projects_projecttask',
        'projects_producttask',
        'projects_taskassignment',
        'projects_timesession',
        'projects_dailytimetotal',
        'projects_product',
        'projects_productsubcategory',
        'projects_projectstatusoption',
        'projects_projectstatushistory',
        'projects_dailyroster',
        'projects_mischours',
        
        # Video production app (4 tables - excluding videoprojectdelivery)
        'video_production_videoproduct',
        'video_production_videoproject',
        'video_production_videoprojectstatushistory',
        'video_production_videoprojectstatusoption',
    ]
    
    def __init__(self, shared_drive_id, service_account_file):
        """
        Initialize backup configuration.
        
        Args:
            shared_drive_id: Google Shared Drive ID (not a regular folder!)
            service_account_file: Path to Google service account JSON key file
        """
        self.shared_drive_id = shared_drive_id
        self.backup_folder = '/tmp/taskpro_backups'
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.date_str = datetime.now().strftime('%Y-%m-%d')
        
        # Setup Google Drive API
        SCOPES = ['https://www.googleapis.com/auth/drive']
        
        try:
            creds = service_account.Credentials.from_service_account_file(
                service_account_file, scopes=SCOPES)
            self.drive_service = build('drive', 'v3', credentials=creds)
            print("✓ Connected to Google Drive API")
            
            # Verify access to Shared Drive
            self._verify_shared_drive_access()
            
        except Exception as e:
            print(f"✗ Failed to connect to Google Drive: {str(e)}")
            sys.exit(1)
    
    def _verify_shared_drive_access(self):
        """Verify that service account has access to the Shared Drive"""
        try:
            drive = self.drive_service.drives().get(driveId=self.shared_drive_id).execute()
            print(f"✓ Access verified to Shared Drive: {drive['name']}\n")
        except Exception as e:
            print(f"\n⚠️  WARNING: Could not verify Shared Drive access")
            print(f"   Error: {str(e)}")
            print(f"\n   Make sure:")
            print(f"   1. This is a Shared Drive ID (not a regular folder)")
            print(f"   2. Service account is added as a member of the Shared Drive")
            print(f"   3. Service account has 'Content Manager' or 'Manager' role\n")
    
    def get_table_data(self, table_name):
        """
        Get data from a specific table.
        
        Args:
            table_name: Name of the database table
            
        Returns:
            DataFrame with table data, or None if failed
        """
        try:
            query = f"SELECT * FROM {table_name}"
            df = pd.read_sql(query, connection)
            return df
        except Exception as e:
            print(f"  ✗ Error reading {table_name}: {str(e)}")
            return None
    
    def create_excel_with_all_tables(self):
        """
        Create a single Excel file with all tables as separate sheets.
        
        Returns:
            filepath: Path to the created Excel file, or None if failed
        """
        try:
            # Create backup folder if doesn't exist
            os.makedirs(self.backup_folder, exist_ok=True)
            
            # Generate filename with timestamp
            filename = f"taskpro_backup_{self.timestamp}.xlsx"
            filepath = os.path.join(self.backup_folder, filename)
            
            print(f"📝 Creating Excel file with {len(self.TABLES_TO_BACKUP)} sheets...\n")
            
            # Create Excel writer
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                successful_sheets = 0
                failed_tables = []
                
                for i, table_name in enumerate(self.TABLES_TO_BACKUP, 1):
                    print(f"[{i}/{len(self.TABLES_TO_BACKUP)}] Processing {table_name}...")
                    
                    # Get table data
                    df = self.get_table_data(table_name)
                    
                    if df is not None:
                        # Create sheet name (Excel has 31 char limit)
                        # Remove app prefix for cleaner sheet names
                        sheet_name = table_name.replace('projects_', '').replace('video_production_', 'vp_').replace('locations_', '')
                        
                        # Truncate if still too long
                        if len(sheet_name) > 31:
                            sheet_name = sheet_name[:31]
                        
                        # Write to Excel sheet
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        
                        print(f"  ✓ Added sheet: {sheet_name} ({len(df)} rows)")
                        successful_sheets += 1
                    else:
                        failed_tables.append(table_name)
                        print(f"  ✗ Skipped {table_name}")
            
            # Get file size for logging
            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            
            print(f"\n✓ Excel file created: {filename}")
            print(f"  → {successful_sheets} sheets, {file_size_mb:.2f} MB")
            
            if failed_tables:
                print(f"\n⚠️  Failed tables: {', '.join(failed_tables)}")
            
            return filepath
            
        except Exception as e:
            print(f"\n✗ Error creating Excel file: {str(e)}")
            return None
    
    def upload_to_drive(self, filepath):
        """
        Upload file to Google Shared Drive.
        
        Args:
            filepath: Local path to the file to upload
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        try:
            print(f"\n📤 Uploading to Shared Drive...")
            
            file_metadata = {
                'name': os.path.basename(filepath),
                'parents': [self.shared_drive_id]
            }
            
            media = MediaFileUpload(filepath, resumable=True)
            
            # IMPORTANT: For Shared Drives, use supportsAllDrives=True
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, size, webViewLink',
                supportsAllDrives=True  # Critical for Shared Drives!
            ).execute()
            
            # Get uploaded file info
            file_size_mb = int(file.get('size', 0)) / (1024 * 1024)
            
            print(f"✓ Upload successful!")
            print(f"  → File ID: {file.get('id')}")
            print(f"  → Size: {file_size_mb:.2f} MB")
            print(f"  → Link: {file.get('webViewLink')}")
            
            return True
            
        except Exception as e:
            print(f"✗ Upload failed: {str(e)}")
            return False
    
    def cleanup_local_files(self):
        """Remove local backup files after upload"""
        try:
            file_count = 0
            for file in os.listdir(self.backup_folder):
                filepath = os.path.join(self.backup_folder, file)
                os.remove(filepath)
                file_count += 1
            
            os.rmdir(self.backup_folder)
            print(f"\n✓ Cleaned up {file_count} local file(s)")
        except Exception as e:
            print(f"\n✗ Cleanup error: {str(e)}")
    
    def cleanup_old_backups(self, days_to_keep=30):
        """
        Delete backups older than specified days from Shared Drive.
        
        Args:
            days_to_keep: Number of days to keep backups (default: 30)
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            
            # Query for old backup files in Shared Drive
            query = f"'{self.shared_drive_id}' in parents and name contains 'taskpro_backup_' and createdTime < '{cutoff_date}'"
            
            results = self.drive_service.files().list(
                q=query,
                fields='files(id, name, createdTime)',
                pageSize=1000,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora='drive',
                driveId=self.shared_drive_id
            ).execute()
            
            files = results.get('files', [])
            
            if files:
                print(f"\n🗑️  Cleaning up old backups (older than {days_to_keep} days):")
                for file in files:
                    self.drive_service.files().delete(
                        fileId=file['id'],
                        supportsAllDrives=True
                    ).execute()
                    print(f"  ✓ Deleted: {file['name']}")
                
                print(f"✓ Removed {len(files)} old backup file(s)")
            else:
                print(f"\n✓ No old backups to clean up")
                
        except Exception as e:
            print(f"\n✗ Cleanup error: {str(e)}")
    
    def run_backup(self):
        """Main backup process"""
        
        print("\n" + "="*70)
        print(f"📦 TaskPro Database Backup")
        print(f"📅 Date: {self.date_str}")
        print(f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}")
        print("="*70 + "\n")
        
        print(f"📋 Tables to backup: {len(self.TABLES_TO_BACKUP)}")
        print(f"📄 Output: Single Excel file with multiple sheets\n")
        
        # Create Excel file with all tables
        excel_file = self.create_excel_with_all_tables()
        
        if not excel_file:
            print("\n❌ Backup failed: Could not create Excel file")
            return
        
        # Upload to Shared Drive
        upload_success = self.upload_to_drive(excel_file)
        
        # Cleanup local files
        self.cleanup_local_files()
        
        # Cleanup old backups from Shared Drive
        self.cleanup_old_backups(days_to_keep=7)
        
        # Summary
        print("\n" + "="*70)
        print("📊 BACKUP SUMMARY")
        print("="*70)
        
        if upload_success:
            print("✅ Backup completed successfully!")
            print(f"   Single Excel file with {len(self.TABLES_TO_BACKUP)} table sheets uploaded")
        else:
            print("⚠️  Backup completed with errors")
            print("   Excel file created but upload failed")
        
        print("="*70)
        print(f"🕐 Completed at: {datetime.now().strftime('%H:%M:%S')}\n")


if __name__ == "__main__":
    """
    Main execution block - Configure your settings here
    """
    
    # ==================== CONFIGURATION ====================
    
    # Google SHARED DRIVE ID (NOT a regular folder!)
    SHARED_DRIVE_ID = '0AHW-ZGa6TVhSUk9PVA'
    
    # Path to Google service account JSON key file
    SERVICE_ACCOUNT_FILE = '/home/deeghalbhaumik/service-account-key.json'
    
    # =======================================================
    
    # Validate configuration
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"\n❌ ERROR: Service account key file not found!")
        print(f"   Expected location: {SERVICE_ACCOUNT_FILE}")
        print("   Please upload your service-account-key.json to PythonAnywhere.\n")
        sys.exit(1)
    
    # Run backup
    try:
        backup = DatabaseBackup(SHARED_DRIVE_ID, SERVICE_ACCOUNT_FILE)
        backup.run_backup()
    except KeyboardInterrupt:
        print("\n\n⚠️  Backup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)