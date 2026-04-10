#!/usr/bin/env python3
"""
sync_download_from_colab.py
=============================
Download trained models from Google Drive after Colab training.

Usage:
    python sync_download_from_colab.py

This will:
- Authenticate with Google Drive
- Find latest models backup
- Download models to backend/models/
- Download evaluation results
"""

import os
import sys
import zipfile
import argparse
from pathlib import Path
from datetime import datetime

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("❌ Missing dependencies. Install with:")
    print("   pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    sys.exit(1)

import io

# Configuration
SCOPES = ['https://www.googleapis.com/auth/drive']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'
COLAB_FOLDER_NAME = 'stock-prediction-backups'


def get_credentials():
    """Authenticate with Google Drive using OAuth."""
    creds = None
    
    # Try to load cached token
    if os.path.exists(TOKEN_FILE):
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


def find_folder(service, folder_name):
    """Find folder by name."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, spaces='drive', pageSize=10, 
                                    fields='files(id, name)').execute()
    folders = results.get('files', [])
    return folders[0]['id'] if folders else None


def list_files_in_folder(service, folder_id):
    """List all files in a folder."""
    query = f"'{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, spaces='drive', pageSize=100,
                                    fields='files(id, name, modifiedTime)').execute()
    return results.get('files', [])


def download_file(service, file_id, file_name, destination):
    """Download file from Google Drive."""
    print(f"   📥 Downloading: {file_name}...", end='', flush=True)
    
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    
    done = False
    while not done:
        status, done = downloader.next_chunk()
    
    # Write to destination
    with open(destination, 'wb') as f:
        f.write(fh.getvalue())
    
    size_mb = os.path.getsize(destination) / 1024 / 1024
    print(f" ✅ ({size_mb:.1f} MB)")
    return destination


def extract_models_from_zip(zip_path, extract_to='backend/models'):
    """Extract models directory from zip."""
    print(f"   📦 Extracting models...")
    os.makedirs(extract_to, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as z:
        # Find all model files in zip
        for member in z.namelist():
            if 'backend/models' in member:
                # Extract, preserving structure
                z.extract(member, path='.')
    
    print(f"   ✅ Models extracted to {extract_to}/")


def main():
    parser = argparse.ArgumentParser(description='Download trained models from Colab')
    parser.add_argument('--latest', action='store_true', default=True,
                        help='Download latest models (default)')
    parser.add_argument('--date', type=str, help='Download models from specific date (YYYYMMDD_HHMMSS)')
    args = parser.parse_args()
    
    print("🚀 Stock Prediction — Colab Sync Downloader")
    print("=" * 50)
    
    # Check for credentials file
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"\n❌ Missing {CREDENTIALS_FILE}")
        print("   This should exist from running sync_upload_to_colab.py first")
        sys.exit(1)
    
    # Authenticate
    print("\n🔐 Authenticating with Google Drive...")
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)
    print("✅ Authentication successful")
    
    # Find backups folder
    print(f"\n📁 Finding '{COLAB_FOLDER_NAME}' folder...")
    folder_id = find_folder(service, COLAB_FOLDER_NAME)
    
    if not folder_id:
        print(f"❌ Folder '{COLAB_FOLDER_NAME}' not found on Drive")
        print("   Please run sync_upload_to_colab.py and train on Colab first")
        sys.exit(1)
    
    # List available models
    print(f"\n📂 Available backups:")
    files = list_files_in_folder(service, folder_id)
    
    if not files:
        print("   ❌ No backups found")
        sys.exit(1)
    
    # Sort by modified time (newest first)
    files.sort(key=lambda x: x['modifiedTime'], reverse=True)
    
    # Find models zip
    models_file = None
    for f in files:
        print(f"   - {f['name']} ({f['modifiedTime']})")
        if f['name'].startswith('models_'):
            models_file = f
            break
    
    if not models_file:
        print(f"\n❌ No models zip file found in backups")
        sys.exit(1)
    
    # Download models
    print(f"\n☁️  Downloading from Google Drive...")
    temp_zip = f"/tmp/{models_file['name']}.zip"
    download_file(service, models_file['id'], models_file['name'], temp_zip)
    
    # Extract models
    print(f"\n📦 Extracting models to local project...")
    extract_models_from_zip(temp_zip)
    
    # Download evaluation results
    print(f"\n📊 Checking for evaluation results...")
    eval_file = None
    for f in files:
        if f['name'] == 'evaluation_results.json':
            eval_file = f
            break
    
    if eval_file:
        eval_dest = 'evaluation_results.json'
        download_file(service, eval_file['id'], eval_file['name'], eval_dest)
        print(f"   📊 Evaluation results saved to {eval_dest}")
    
    # Cleanup
    os.remove(temp_zip)
    
    print("\n" + "=" * 50)
    print("✅ Download complete!")
    print(f"\n📍 Models synced to: backend/models/")
    print(f"📊 Evaluation results: evaluation_results.json")
    print(f"\n🎯 Next steps:")
    print(f"   1. Review models in backend/models/RELIANCE.NS/ and TCS.NS/")
    print(f"   2. Check evaluation_results.json for metrics")
    print(f"   3. Use the models in your backend or analysis")


if __name__ == '__main__':
    main()
