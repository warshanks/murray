"""Module for managing document uploads and workspace updates in AnythingLLM."""

import os
import json
from pathlib import Path
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

ANYTHINGLLM_API_KEY = os.getenv('ANYTHINGLLM_API_KEY')
ANYTHINGLLM_BASE_URL = os.getenv('ANYTHINGLLM_BASE_URL')
UPLOAD_TRACKER_FILE = 'uploaded_files.json'

def load_uploaded_files():
    """
    Load the dictionary of previously uploaded files from the tracker file.

    Returns:
        dict: Dictionary containing file hashes as keys and file paths as values.
    """
    if os.path.exists(UPLOAD_TRACKER_FILE):
        with open(UPLOAD_TRACKER_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_uploaded_files(uploaded_files_dict):
    """
    Save the dictionary of uploaded files to the tracker file.

    Args:
        uploaded_files_dict (dict): Dictionary containing file hashes as keys and file paths as values.
    """
    with open(UPLOAD_TRACKER_FILE, 'w', encoding='utf-8') as f:
        json.dump(uploaded_files_dict, f, indent=2)

def process_new_documents(new_files):
    """
    Process a list of newly downloaded files and upload them to AnythingLLM.

    Args:
        new_files: List of paths to newly downloaded files

    Returns:
        List of successfully uploaded file locations
    """
    if not new_files:
        return []

    uploaded_files = []
    uploaded_files_tracker = load_uploaded_files()

    for file_path in new_files:
        file_path = Path(file_path)
        if not file_path.is_file() or file_path.suffix.lower() != '.pdf':
            continue

        file_hash = str(os.path.getsize(file_path))
        if file_hash in uploaded_files_tracker and uploaded_files_tracker[file_hash] == str(file_path):
            print(f"Skipping {file_path.name} - already uploaded")
            continue

        print(f"Uploading {file_path.name}...")

        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f)}
                response = requests.post(
                    f"{ANYTHINGLLM_BASE_URL}/document/upload",
                    headers={'Authorization': f'Bearer {ANYTHINGLLM_API_KEY}'},
                    files=files,
                    timeout=300
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        uploaded_files.extend(doc['location'] for doc in result['documents'])
                        uploaded_files_tracker[file_hash] = str(file_path)
                        save_uploaded_files(uploaded_files_tracker)
                        print(f"Successfully uploaded {file_path.name}")
                    else:
                        print(f"Failed to upload {file_path.name}: {result.get('error')}")
                else:
                    print(f"Error uploading {file_path.name}: {response.status_code}")
        except Exception as e:
            print(f"Exception while uploading {file_path.name}: {str(e)}")

    return uploaded_files

def upload_documents(directory: str):
    """
    Upload all PDF documents from a specified directory to AnythingLLM.

    Args:
        directory (str): Path to the directory containing PDF files.

    Returns:
        list: List of successfully uploaded file locations.
    """
    documents_dir = Path(directory)
    files_to_process = [f for f in documents_dir.glob('*.pdf') if f.is_file()]
    return process_new_documents(files_to_process)

def move_files_to_folder(files, target_folder):
    """
    Move files to a specified target folder in AnythingLLM.

    Args:
        files (list): List of file paths to move.
        target_folder (str): Target folder path in AnythingLLM.

    Returns:
        list: List of new file paths after moving, or None if the operation failed.
    """
    headers = {
        'Authorization': f'Bearer {ANYTHINGLLM_API_KEY}',
        'Content-Type': 'application/json'
    }

    moves = [{"from": file, "to": f"{target_folder}/{Path(file).name}"} for file in files]

    response = requests.post(
        f"{ANYTHINGLLM_BASE_URL}/document/move-files",
        headers=headers,
        json={"files": moves},
        timeout=300
    )

    if response.status_code == 200:
        print("Successfully moved files to murray folder")
        return [move["to"] for move in moves]
    else:
        print(f"Error moving files: {response.status_code}")
        return None

def update_workspace_embeddings(workspace_slug, file_paths):
    """
    Update the workspace embeddings for a given workspace slug.

    Args:
        workspace_slug (str): The unique identifier for the workspace.
        file_paths (list): List of file paths to update embeddings for.
    """
    headers = {
        'Authorization': f'Bearer {ANYTHINGLLM_API_KEY}',
        'Content-Type': 'application/json'
    }

    response = requests.post(
        f"{ANYTHINGLLM_BASE_URL}/workspace/{workspace_slug}/update-embeddings",
        headers=headers,
        json={
            "adds": file_paths,
            "deletes": []
        },
        timeout=300
    )

    if response.status_code == 200:
        print("Successfully updated workspace embeddings")
    else:
        print(f"Error updating workspace embeddings: {response.status_code}")

def main():
    """
    Main function to execute the document upload and workspace update process.

    This function performs three main steps:
    1. Uploads documents from the ./documents directory
    2. Moves the uploaded files to the murray folder
    3. Updates the workspace embeddings with the new files
    """
    # 1. Upload documents
    uploaded_files = upload_documents("./documents")
    if not uploaded_files:
        print("No files were uploaded successfully")
        return

    # 2. Move files to murray folder
    moved_files = move_files_to_folder(uploaded_files, "murray")
    if not moved_files:
        print("Failed to move files")
        return

    # 3. Update workspace embeddings
    # Extract workspace slug from ANYTHINGLLM_ENDPOINT
    workspace_slug = os.getenv('ANYTHINGLLM_ENDPOINT').split('workspace/')[-1].split('/')[0]
    update_workspace_embeddings(workspace_slug, moved_files)

if __name__ == "__main__":
    main()
