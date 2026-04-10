#!/usr/bin/env python3
"""
sync_upload_to_colab.py
=======================
Upload local project to Google Drive for Colab training.

Usage:
    python sync_upload_to_colab.py

Requirements:
    - Google account with Drive access
    - First run: Follow OAuth link to authenticate
    - Subsequent runs: Auto-authenticated via cached token
"""

import os
import sys
import zipfile
import argparse
from pathlib import Path
from datetime import datetime

try:
    from google.auth.transport.requests import Request
    from google.oauth2.service_account import Credentials
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("❌ Missing dependencies. Install with:")
    print("   pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    sys.exit(1)

# Configuration
SCOPES = ['https://www.googleapis.com/auth/drive']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'
COLAB_FOLDER_NAME = 'stock-prediction'
BACKUPS_FOLDER_NAME = 'stock-prediction-backups'

# Directories to exclude from zip
EXCLUDE_DIRS = {'.venv', '__pycache__', '.git', 'node_modules', '.pytest_cache', 
                '.ipynb_checkpoints', 'venv', 'env', 'site-packages', '.egg-info'}
EXCLUDE_FILES = {'.DS_Store', '*.pyc', '*.pyo', '*.pyd', '*.egg-info'}


def get_credentials():
    """Authenticate with Google Drive using OAuth."""
    creds = None
    
    # Try to load cached token
    if os.path.exists(TOKEN_FILE):
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # If no valid credentials, request new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for future use
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return creds


def find_or_create_folder(service, parent_id, folder_name):
    """Find folder by name, or create if doesn't exist."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, spaces='drive', pageSize=10, 
                                    fields='files(id, name)').execute()
    folders = results.get('files', [])
    
    if folders:
        return folders[0]['id']
    else:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id] if parent_id else []
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        print(f"✅ Created folder: {folder_name}")
        return folder['id']


def create_project_zip(exclude_patterns=None):
    """Create zip file of project, excluding unnecessary dirs."""
    if exclude_patterns is None:
        exclude_patterns = EXCLUDE_DIRS
    
    project_root = Path.cwd()
    zip_name = f"stock-prediction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    zip_path = project_root / zip_name
    
    print(f"📦 Creating project zip: {zip_name}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(project_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_patterns]
            
            for file in files:
                # Skip excluded file types
                if any(file.endswith(ext) for ext in ['.pyc', '.pyo', '.pyd', '.DS_Store']):
                    continue
                
                file_path = Path(root) / file
                arcname = file_path.relative_to(project_root.parent)
                z.write(file_path, arcname)
    
    size_mb = zip_path.stat().st_size / 1024 / 1024
    print(f"✅ Zip created: {zip_path.name} ({size_mb:.1f} MB)")
    return str(zip_path)


def upload_file_to_drive(service, file_path, folder_id, file_name=None):
    """Upload file to Google Drive folder."""
    if file_name is None:
        file_name = Path(file_path).name
    
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    
    media = MediaFileUpload(file_path, resumable=True)
    request = service.files().create(body=file_metadata, media_body=media, fields='id')
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            progress = int(status.progress() * 100)
            print(f"   {progress}% uploaded...", end='\r')
    
    print(f"✅ Uploaded: {file_name}")
    return response.get('id')


def main():
    parser = argparse.ArgumentParser(description='Upload project to Google Drive for Colab training')
    parser.add_argument('--no-auth', action='store_true', help='Skip authentication (for testing)')
    args = parser.parse_args()
    
    print("🚀 Stock Prediction — Colab Sync Uploader")
    print("=" * 50)
    
    # Check for credentials file
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"\n❌ Missing {CREDENTIALS_FILE}")
        print("\nSetup instructions:")
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Create a new project")
        print("3. Enable 'Google Drive API'")
        print("4. Create OAuth 2.0 Desktop credentials")
        print("5. Download as JSON and save as: credentials.json")
        print("\nOr use service account JSON from GCP.")
        sys.exit(1)
    
    if args.no_auth:
        print("⏭️  Skipping authentication")
        zip_path = create_project_zip()
        print(f"\n✅ Ready to upload: {zip_path}")
        return
    
    # Authenticate
    print("\n🔐 Authenticating with Google Drive...")
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)
    print("✅ Authentication successful")
    
    # Get root "My Drive" folder ID
    results = service.files().list(spaces='drive', pageSize=1, 
                                    fields='files(id, name)', corpora='user').execute()
    root_id = results['files'][0]['id'] if results['files'] else 'root'
    
    # Find or create project folder
    print(f"\n📁 Locating '{COLAB_FOLDER_NAME}' folder...")
    project_folder_id = find_or_create_folder(service, root_id, COLAB_FOLDER_NAME)
    
    # Find or create backups folder
    backups_folder_id = find_or_create_folder(service, project_folder_id, 'backups')
    
    # Create and upload zip
    print("\n📦 Preparing project for upload...")
    zip_path = create_project_zip()
    
    print(f"\n☁️  Uploading to Google Drive...")
    upload_file_to_drive(service, zip_path, project_folder_id)
    
    # Keep a backup
    backup_zip = f"stock-prediction-backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    upload_file_to_drive(service, zip_path, backups_folder_id, backup_zip)
    
    print("\n" + "=" * 50)
    print("✅ Upload complete!")
    print(f"\n📍 Your project is ready on Google Drive:")
    print(f"   Folder: {COLAB_FOLDER_NAME}/")
    print(f"   Zip: stock-prediction.zip")
    print(f"\n🔗 Next steps:")
    print(f"   1. Open: https://colab.research.google.com/")
    print(f"   2. Upload colab_trainer.ipynb from this project")
    print(f"   3. Run all cells in the notebook")
    print(f"\n💾 Models will be saved to:")
    print(f"   {COLAB_FOLDER_NAME}/backups/models_*")


if __name__ == '__main__':
    main()
