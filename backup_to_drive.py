#!/usr/bin/env python
"""
Database Backup Script for TaskPro - Shared Drive Version
Exports all database tables to Excel and uploads to Google Shared Drive

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
    Uses service account authentication for corporate accounts.
    """
    
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
            # Try to get Shared Drive info
            drive = self.drive_service.drives().get(driveId=self.shared_drive_id).execute()
            print(f"✓ Access verified to Shared Drive: {drive['name']}")
        except Exception as e:
            print(f"\n⚠️  WARNING: Could not verify Shared Drive access")
            print(f"   Error: {str(e)}")
            print(f"\n   Make sure:")
            print(f"   1. This is a Shared Drive ID (not a regular folder)")
            print(f"   2. Service account is added as a member of the Shared Drive")
            print(f"   3. Service account has 'Content Manager' or 'Manager' role\n")
    
    def get_all_tables(self):
        """Get list of all tables from MySQL database"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = [row[0] for row in cursor.fetchall()]
            print(f"✓ Found {len(tables)} tables in database")
            return tables
        except Exception as e:
            print(f"✗ Error getting table list: {str(e)}")
            return []
    
    def export_table_to_excel(self, table_name):
        """
        Export a single table to Excel using pandas.
        
        Args:
            table_name: Name of the database table to export
            
        Returns:
            filepath: Path to the created Excel file, or None if failed
        """
        try:
            # Read table data using pandas
            query = f"SELECT * FROM {table_name}"
            df = pd.read_sql(query, connection)
            
            # Create backup folder if doesn't exist
            os.makedirs(self.backup_folder, exist_ok=True)
            
            # Generate filename with timestamp
            filename = f"{table_name}_{self.timestamp}.xlsx"
            filepath = os.path.join(self.backup_folder, filename)
            
            # Export to Excel
            df.to_excel(filepath, index=False, engine='openpyxl')
            
            # Get file size for logging
            file_size_kb = os.path.getsize(filepath) / 1024
            
            print(f"  ✓ Exported {table_name}")
            print(f"    → {len(df)} rows, {file_size_kb:.2f} KB")
            
            return filepath
            
        except Exception as e:
            print(f"  ✗ Error exporting {table_name}: {str(e)}")
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
            file_metadata = {
                'name': os.path.basename(filepath),
                'parents': [self.shared_drive_id]
            }
            
            media = MediaFileUpload(filepath, resumable=True)
            
            # IMPORTANT: For Shared Drives, use supportsAllDrives=True
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, size',
                supportsAllDrives=True  # Critical for Shared Drives!
            ).execute()
            
            # Get uploaded file size
            file_size_mb = int(file.get('size', 0)) / (1024 * 1024)
            
            print(f"    → Uploaded to Shared Drive ({file_size_mb:.2f} MB)")
            return True
            
        except Exception as e:
            print(f"    ✗ Upload failed: {str(e)}")
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
            print(f"\n✓ Cleaned up {file_count} local files")
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
            
            # Query for old files in Shared Drive
            query = f"'{self.shared_drive_id}' in parents and createdTime < '{cutoff_date}'"
            
            results = self.drive_service.files().list(
                q=query,
                fields='files(id, name, createdTime)',
                pageSize=1000,
                supportsAllDrives=True,  # Critical for Shared Drives!
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
                        supportsAllDrives=True  # Critical for Shared Drives!
                    ).execute()
                    print(f"  ✓ Deleted: {file['name']}")
                
                print(f"✓ Removed {len(files)} old backup files")
            else:
                print(f"\n✓ No old backups to clean up")
                
        except Exception as e:
            print(f"\n✗ Cleanup error: {str(e)}")
    
    def run_backup(self):
        """Main backup process - orchestrates the entire backup workflow"""
        
        print("\n" + "="*70)
        print(f"📦 TaskPro Database Backup")
        print(f"📅 Date: {self.date_str}")
        print(f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}")
        print("="*70 + "\n")
        
        # Get all tables
        print("📋 Scanning database...")
        tables = self.get_all_tables()
        
        if not tables:
            print("\n✗ No tables found. Backup aborted.")
            return
        
        successful_uploads = 0
        failed_tables = []
        
        print(f"\n💾 Starting backup of {len(tables)} tables...\n")
        
        # Backup each table
        for i, table in enumerate(tables, 1):
            print(f"[{i}/{len(tables)}] {table}")
            
            # Export to Excel
            filepath = self.export_table_to_excel(table)
            
            if filepath:
                # Upload to Shared Drive
                if self.upload_to_drive(filepath):
                    successful_uploads += 1
                else:
                    failed_tables.append(table)
            else:
                failed_tables.append(table)
        
        # Cleanup local files
        self.cleanup_local_files()
        
        # Cleanup old backups from Shared Drive
        self.cleanup_old_backups(days_to_keep=30)
        
        # Summary
        print("\n" + "="*70)
        print("📊 BACKUP SUMMARY")
        print("="*70)
        print(f"  Total tables:      {len(tables)}")
        print(f"  ✓ Successful:      {successful_uploads}")
        print(f"  ✗ Failed:          {len(failed_tables)}")
        
        if failed_tables:
            print(f"\n  Failed tables:")
            for table in failed_tables:
                print(f"    • {table}")
        
        print("="*70)
        
        if successful_uploads == len(tables):
            print("\n✅ Backup completed successfully!")
        else:
            print(f"\n⚠️  Backup completed with {len(failed_tables)} errors")
        
        print(f"🕐 Completed at: {datetime.now().strftime('%H:%M:%S')}\n")


if __name__ == "__main__":
    """
    Main execution block - Configure your settings here
    """
    
    # ==================== CONFIGURATION ====================
    # TODO: Update these values with your actual credentials
    
    # Google SHARED DRIVE ID (NOT a regular folder!)
    # Get this from the Shared Drive URL in Google Drive
    # Example URL: https://drive.google.com/drive/folders/0ABC-defGHijKLmnoPqr
    # Shared Drive ID is: 0ABC-defGHijKLmnoPqr
    SHARED_DRIVE_ID = '0AHW-ZGa6TVhSUk9PVA'
    
    # Path to Google service account JSON key file
    SERVICE_ACCOUNT_FILE = '/home/deeghalbhaumik/service-account-key.json'
    
    # =======================================================
    
    # Validate configuration
    if SHARED_DRIVE_ID == 'YOUR_SHARED_DRIVE_ID_HERE':
        print("\n❌ ERROR: Please configure SHARED_DRIVE_ID in the script!")
        print("   Edit backup_to_drive.py and replace 'YOUR_SHARED_DRIVE_ID_HERE'")
        print("   with your actual Google Shared Drive ID.\n")
        print("   NOTE: This must be a SHARED DRIVE, not a regular folder!\n")
        sys.exit(1)
    
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