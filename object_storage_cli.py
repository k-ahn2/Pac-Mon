#!/usr/bin/env python3
"""
Container Storage CLI

A simple command-line tool for browsing folders and managing files from within a container.
This tool uses the container IP-based authentication to access storage without requiring
explicit authentication. It can also use token-based authentication when running outside
of a container.

Usage:
  # Interactive mode
  python container_storage_cli.py

  # Command-line mode
  python container_storage_cli.py --list-folders
  python container_storage_cli.py --browse-folder <folder_id>
  python container_storage_cli.py --download <file_id> --output <path>
  python container_storage_cli.py --download <file_id> --stdout
  python container_storage_cli.py --upload <file_path> --folder <folder_id>
  python container_storage_cli.py --upload <file_path> --folder <folder_id> --upload-as <filename>
  python container_storage_cli.py --stdin --upload-as <filename> --folder <folder_id>
  python container_storage_cli.py --file-info <file_id>

  # Sync directories (rsync-like)
  python container_storage_cli.py --sync ./local-dir --folder-path "Default/remote-dir"
  python container_storage_cli.py --sync ./local-dir --folder <folder_id> --delete
  python container_storage_cli.py --sync ./local-dir --folder-path "Default/remote-dir" --delete --dry-run

  # JSON output
  python container_storage_cli.py --list-folders --json
  python container_storage_cli.py --file-info <file_id> --json

  # Configuration
  python container_storage_cli.py --configure
  python container_storage_cli.py --token <your_token>

  # Upload from stdin
  echo "Hello World" | python container_storage_cli.py --stdin --upload-as hello.txt --folder <folder_id>
  cat file.txt | python container_storage_cli.py --stdin --upload-as remote_file.txt --folder <folder_id>

  # Download to stdout
  python container_storage_cli.py --download <file_id> --stdout > local_file.txt
  python container_storage_cli.py --download <file_id> --stdout | grep "pattern"

Features:
  - Browse folders
  - Download files to filesystem or stdout
  - Upload files from filesystem or stdin
  - Sync local directories to remote folders (rsync-like with MD5 comparison)
  - Command-line interface for scripting
  - JSON output for programmatic use
  - Get detailed information about files
  - Token-based authentication for use outside containers
"""

import os
import sys
import requests
import json
import argparse
import configparser
import getpass
import hashlib

# Configuration
def get_default_storage_url():
    """
    Dynamically select the default storage URL based on environment.
    If /dev/incus/sock exists, we're likely inside a container, use ENVOY_PUBLIC_IP.
    Otherwise, use BASE_URL for external access.
    """
    if os.path.exists('/dev/incus/sock'):
        # Inside container - use ENVOY_PUBLIC_IP with port 5003 (object storage API port)
        return 'http://44.31.241.65:5003'
    else:
        # Outside container - use BASE_URL
        return 'https://compute.oarc.uk'

BASE_URL = os.environ.get('STORAGE_API_URL', get_default_storage_url())
CONFIG_PATH = os.path.expanduser("~/.compute/config")
TOKEN = None

def load_config():
    """Load configuration from the config file."""
    global TOKEN

    config = configparser.ConfigParser()

    # Check if config file exists
    if os.path.exists(CONFIG_PATH):
        config.read(CONFIG_PATH)

        # Get token from config if it exists
        if 'storage' in config and 'token' in config['storage']:
            TOKEN = config['storage']['token']

def save_config(token):
    """Save the token to the config file."""
    config = configparser.ConfigParser()

    # Create sections if they don't exist
    if os.path.exists(CONFIG_PATH):
        config.read(CONFIG_PATH)

    if 'storage' not in config:
        config['storage'] = {}

    # Update config with token
    config['storage']['token'] = token

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

    # Write config to file
    with open(CONFIG_PATH, 'w') as f:
        config.write(f)

    # Set appropriate permissions (read/write for user only)
    os.chmod(CONFIG_PATH, 0o600)

    return True

def prompt_for_token():
    """Prompt the user for their API token."""
    print("API token not found. Please enter your API token.")
    print("You can find your token in your user profile page.")
    token = getpass.getpass("API Token: ").strip()

    # Save the token to config
    if token:
        save_config_choice = input("Save token to config file? (y/n): ").lower().strip()
        if save_config_choice == 'y':
            if save_config(token):
                print(f"Token saved to {CONFIG_PATH}")

    return token

class ContainerStorageCLI:
    def __init__(self, json_output=False, token=None):
        self.current_folder = None
        self.folder_stack = []
        self.accessible_folders = []
        self.current_files = []
        self.current_subfolders = []
        self.json_output = json_output
        self.token = token
        self.folder_display_map = {}  # Maps display index to folder data

    def get_headers(self):
        """Get the headers for API requests."""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def initialize(self):
        """Initialize the CLI by checking for accessible folders"""
        if not self.json_output:
            print("Initializing Container Storage CLI...")
        try:
            # Get all accessible folders (works with both container IP auth and token auth)
            response = requests.get(
                f"{BASE_URL}/storage/api/accessible-folders",
                headers=self.get_headers()
            )

            if response.status_code == 401:
                if self.json_output:
                    self.output_json({"error": "This container does not have access to any folders"})
                    sys.exit(1)
                else:
                    print("\n❌ ERROR: This container does not have access to any folders.")
                    print("Please ask your administrator to grant this container access to at least one folder.")
                    print("They can do this by clicking the 'Container' button on a folder in the web interface.")
                    sys.exit(1)

            if response.status_code != 200:
                if self.json_output:
                    self.output_json({"error": f"Failed to get accessible folders. Status code: {response.status_code}", "response": response.text})
                    sys.exit(1)
                else:
                    print(f"\n❌ ERROR: Failed to get accessible folders. Status code: {response.status_code}")
                    print(f"Response: {response.text}")
                    sys.exit(1)

            self.accessible_folders = response.json()

            if not self.accessible_folders:
                if self.json_output:
                    self.output_json({"error": "This container does not have access to any folders"})
                    sys.exit(1)
                else:
                    print("\n❌ ERROR: This container does not have access to any folders.")
                    print("Please ask your administrator to grant this container access to at least one folder.")
                    print("They can do this by clicking the 'Container' button on a folder in the web interface.")
                    sys.exit(1)

            if not self.json_output:
                print(f"Found {len(self.accessible_folders)} accessible folder(s).")

        except requests.exceptions.RequestException as e:
            if self.json_output:
                self.output_json({"error": f"Failed to connect to the storage API: {e}", "url": BASE_URL})
                sys.exit(1)
            else:
                print(f"\n❌ ERROR: Failed to connect to the storage API: {e}")
                print(f"Make sure the STORAGE_API_URL environment variable is set correctly (current value: {BASE_URL})")
                sys.exit(1)

    def output_json(self, data):
        """Output data as JSON"""
        print(json.dumps(data, indent=2))

    def list_accessible_folders(self):
        """List all folders accessible by this container"""
        if self.json_output:
            self.output_json(self.accessible_folders)
            return

        print("\n📁 Accessible Folders:")

        # Build hierarchy tree
        hierarchy = self._build_folder_hierarchy(self.accessible_folders)

        # Display hierarchy
        self._display_folder_hierarchy(hierarchy)

    def _build_folder_hierarchy(self, folders):
        """Build a hierarchical tree structure from flat folder list"""
        # Create a mapping of folder ID to folder data
        folder_map = {folder['id']: folder for folder in folders}

        # Find root folders (those without parent_id or parent not in accessible folders)
        root_folders = []

        for folder in folders:
            parent_id = folder.get('parent_id')
            if parent_id is None or parent_id not in folder_map:
                # This is a root folder (no parent or parent not accessible)
                root_folders.append(folder)

        # Build the tree structure recursively
        def build_tree(parent_folders):
            tree = []
            for folder in parent_folders:
                folder_node = {
                    'folder': folder,
                    'children': []
                }

                # Find children of this folder
                children = [f for f in folders if f.get('parent_id') == folder['id']]
                if children:
                    folder_node['children'] = build_tree(children)

                tree.append(folder_node)
            return tree

        return build_tree(root_folders)

    def _display_folder_hierarchy(self, hierarchy, level=0, parent_numbers=None):
        """Display folder hierarchy with proper indentation and numbering"""
        if parent_numbers is None:
            parent_numbers = []
            # Reset the display map when starting fresh
            if level == 0:
                self.folder_display_map = {}

        for i, node in enumerate(hierarchy, 1):
            folder = node['folder']

            # Build current numbering path
            current_numbers = parent_numbers + [i]

            # Create indentation
            indent = "  " * level

            # Display size if available
            size_info = ""
            if 'size_formatted' in folder:
                size_info = f", Size: {folder['size_formatted']}"

            # Print folder with hierarchy
            if level == 0:
                # Root level folders - these are selectable
                display_index = i  # Use simple numbering for root level
                self.folder_display_map[display_index] = folder
                print(f"  {display_index}. {folder['name']} (ID: {folder['id']}{size_info})")
            else:
                # Child folders with tree-like display
                tree_char = "└── " if i == len(hierarchy) else "├── "
                print(f"    {indent}{tree_char}{folder['name']} (ID: {folder['id']}{size_info})")

            # Recursively display children
            if node['children']:
                if level == 0:
                    # For root level, continue with numbered hierarchy
                    self._display_folder_hierarchy(node['children'], level + 1, current_numbers)
                else:
                    # For deeper levels, use tree-style display
                    child_indent = "  " * (level + 1)
                    for j, child_node in enumerate(node['children'], 1):
                        child_folder = child_node['folder']
                        child_size_info = f", Size: {child_folder['size_formatted']}" if 'size_formatted' in child_folder else ""

                        child_tree_char = "└── " if j == len(node['children']) else "├── "
                        print(f"    {child_indent}{child_tree_char}{child_folder['name']} (ID: {child_folder['id']}{child_size_info})")

                        # Handle deeper nesting if needed
                        if child_node['children']:
                            self._display_deeper_children(child_node['children'], level + 2)

    def _display_deeper_children(self, children, level):
        """Display children at deeper levels with consistent tree formatting"""
        indent = "  " * level
        for i, child_node in enumerate(children, 1):
            folder = child_node['folder']
            size_info = f", Size: {folder['size_formatted']}" if 'size_formatted' in folder else ""

            tree_char = "└── " if i == len(children) else "├── "
            print(f"    {indent}{tree_char}{folder['name']} (ID: {folder['id']}{size_info})")

            if child_node['children']:
                self._display_deeper_children(child_node['children'], level + 1)

    def select_folder(self, folder_index):
        """Select a folder from the displayed hierarchy"""
        if folder_index not in self.folder_display_map:
            print("❌ Invalid folder index.")
            return False

        # Get the folder from the display map
        folder = self.folder_display_map[folder_index]

        # Fetch the complete folder information including size
        try:
            response = requests.get(
                f"{BASE_URL}/storage/api/folders/{folder['id']}",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                # Update with complete folder information
                self.current_folder = response.json()
            else:
                # Fall back to basic folder info if detailed fetch fails
                self.current_folder = folder
        except Exception:
            # Fall back to basic folder info if request fails
            self.current_folder = folder

        self.folder_stack = [self.current_folder]
        self.refresh_current_folder()
        return True

    def refresh_current_folder(self):
        """Refresh the contents of the current folder"""
        if not self.current_folder:
            if self.json_output:
                self.output_json({"error": "No folder selected"})
                return False
            else:
                print("❌ No folder selected.")
                return False

        # Get files in the current folder
        response = requests.get(
            f"{BASE_URL}/storage/api/files?folder_id={self.current_folder['id']}",
            headers=self.get_headers()
        )
        if response.status_code != 200:
            if self.json_output:
                self.output_json({"error": f"Failed to get files. Status code: {response.status_code}", "response": response.text})
                return False
            else:
                print(f"❌ Failed to get files. Status code: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        self.current_files = response.json()

        # Get subfolders in the current folder
        response = requests.get(
            f"{BASE_URL}/storage/api/folders?parent_id={self.current_folder['id']}",
            headers=self.get_headers()
        )
        if response.status_code != 200:
            if self.json_output:
                self.output_json({"error": f"Failed to get subfolders. Status code: {response.status_code}", "response": response.text})
                return False
            else:
                print(f"❌ Failed to get subfolders. Status code: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        self.current_subfolders = response.json()
        return True

    def display_current_folder(self):
        """Display the contents of the current folder"""
        if not self.current_folder:
            if self.json_output:
                self.output_json({"error": "No folder selected"})
                return
            else:
                print("❌ No folder selected.")
                return

        if self.json_output:
            result = {
                "folder": self.current_folder,
                "path": [folder['name'] for folder in self.folder_stack],
                "subfolders": self.current_subfolders,
                "files": self.current_files
            }
            self.output_json(result)
            return

        # Print current path and size if available
        path = " / ".join([folder['name'] for folder in self.folder_stack])
        size_info = ""
        if 'size_formatted' in self.current_folder:
            size_info = f" ({self.current_folder['size_formatted']})"
        print(f"\n📂 Current path: {path}{size_info}")

        # Print subfolders
        if self.current_subfolders:
            print("\n📁 Subfolders:")
            for i, folder in enumerate(self.current_subfolders, 1):
                # Display size if available
                size_info = ""
                if 'size_formatted' in folder:
                    size_info = f" ({folder['size_formatted']})"
                print(f"  {i}. {folder['name']}{size_info}")
        else:
            print("\n📁 No subfolders.")

        # Print files
        if self.current_files:
            print("\n📄 Files:")
            for i, file in enumerate(self.current_files, 1):
                size = file['size_formatted']
                created = file['created_at']
                print(f"  {i}. {file['name']} ({size}, created: {created})")
        else:
            print("\n📄 No files.")

    def enter_subfolder(self, subfolder_index):
        """Enter a subfolder"""
        if not self.current_folder:
            print("❌ No folder selected.")
            return False

        if subfolder_index < 1 or subfolder_index > len(self.current_subfolders):
            print("❌ Invalid subfolder index.")
            return False

        # Get the basic subfolder info
        subfolder = self.current_subfolders[subfolder_index - 1]

        # Fetch the complete folder information including size
        try:
            response = requests.get(
                f"{BASE_URL}/storage/api/folders/{subfolder['id']}",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                # Update with complete folder information
                subfolder = response.json()
        except Exception:
            # Continue with basic folder info if request fails
            pass

        self.current_folder = subfolder
        self.folder_stack.append(subfolder)
        self.refresh_current_folder()
        return True

    def go_back(self):
        """Go back to the parent folder"""
        if not self.current_folder:
            print("❌ No folder selected.")
            return False

        if len(self.folder_stack) <= 1:
            print("❌ Already at the root folder.")
            return False

        self.folder_stack.pop()  # Remove current folder
        parent_folder = self.folder_stack[-1]  # Get parent folder

        # Fetch the complete folder information including size
        try:
            response = requests.get(
                f"{BASE_URL}/storage/api/folders/{parent_folder['id']}",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                # Update with complete folder information
                self.current_folder = response.json()
            else:
                # Fall back to basic folder info if detailed fetch fails
                self.current_folder = parent_folder
        except Exception:
            # Fall back to basic folder info if request fails
            self.current_folder = parent_folder

        self.refresh_current_folder()
        return True

    def download_file(self, file_index=None, output_path=None, file_id=None, to_stdout=False):
        """Download a file by index or ID"""
        # If file_id is provided, download by ID
        if file_id:
            try:
                if not self.json_output and not to_stdout:
                    print(f"⬇️ Downloading file with ID {file_id}...")

                response = requests.get(
                    f"{BASE_URL}/storage/api/files/{file_id}/download",
                    headers=self.get_headers(),
                    stream=True
                )

                if response.status_code != 200:
                    if self.json_output:
                        self.output_json({"error": f"Failed to download file. Status code: {response.status_code}", "response": response.text})
                        return False
                    else:
                        if not to_stdout:
                            print(f"❌ Failed to download file. Status code: {response.status_code}")
                            print(f"Response: {response.text}")
                        else:
                            # Write error to stderr when using stdout
                            sys.stderr.write(f"❌ Failed to download file. Status code: {response.status_code}\n")
                            sys.stderr.write(f"Response: {response.text}\n")
                        return False

                if to_stdout:
                    # Write directly to stdout
                    for chunk in response.iter_content(chunk_size=8192):
                        sys.stdout.buffer.write(chunk)
                    sys.stdout.buffer.flush()
                    return True

                # Get filename from Content-Disposition header if available
                content_disposition = response.headers.get('Content-Disposition')
                if content_disposition and 'filename=' in content_disposition:
                    filename = content_disposition.split('filename=')[1].strip('"\'')
                else:
                    filename = f"file_{file_id}"

                if not output_path:
                    output_path = filename

                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                if self.json_output:
                    self.output_json({"success": True, "file_id": file_id, "output_path": output_path})
                else:
                    print(f"✅ Downloaded file to {output_path}")
                return True

            except requests.exceptions.RequestException as e:
                if self.json_output:
                    self.output_json({"error": f"Failed to download file: {e}"})
                else:
                    print(f"❌ Failed to download file: {e}")
                return False
            except IOError as e:
                if self.json_output:
                    self.output_json({"error": f"Failed to write file: {e}"})
                else:
                    print(f"❌ Failed to write file: {e}")
                return False

        # Otherwise download by index
        if not self.current_folder:
            if self.json_output:
                self.output_json({"error": "No folder selected"})
            else:
                print("❌ No folder selected.")
            return False

        if file_index < 1 or file_index > len(self.current_files):
            if self.json_output:
                self.output_json({"error": "Invalid file index"})
            else:
                print("❌ Invalid file index.")
            return False

        file = self.current_files[file_index - 1]
        file_id = file['id']
        file_name = file['name']

        if to_stdout:
            # Write directly to stdout
            if not self.json_output:
                sys.stderr.write(f"⬇️ Downloading {file_name} to stdout...\n")

            try:
                response = requests.get(
                    f"{BASE_URL}/storage/api/files/{file_id}/download",
                    headers=self.get_headers(),
                    stream=True
                )

                if response.status_code != 200:
                    if self.json_output:
                        self.output_json({"error": f"Failed to download file. Status code: {response.status_code}", "response": response.text})
                    else:
                        sys.stderr.write(f"❌ Failed to download file. Status code: {response.status_code}\n")
                        sys.stderr.write(f"Response: {response.text}\n")
                    return False

                for chunk in response.iter_content(chunk_size=8192):
                    sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()

                if self.json_output:
                    self.output_json({"success": True, "file": file, "output": "stdout"})
                return True

            except requests.exceptions.RequestException as e:
                if self.json_output:
                    self.output_json({"error": f"Failed to download file: {e}"})
                else:
                    sys.stderr.write(f"❌ Failed to download file: {e}\n")
                return False

        if not output_path:
            output_path = file_name

        if not self.json_output:
            print(f"⬇️ Downloading {file_name}...")

        try:
            response = requests.get(
                f"{BASE_URL}/storage/api/files/{file_id}/download",
                headers=self.get_headers(),
                stream=True
            )

            if response.status_code != 200:
                if self.json_output:
                    self.output_json({"error": f"Failed to download file. Status code: {response.status_code}", "response": response.text})
                else:
                    print(f"❌ Failed to download file. Status code: {response.status_code}")
                    print(f"Response: {response.text}")
                return False

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            if self.json_output:
                self.output_json({"success": True, "file": file, "output_path": output_path})
            else:
                print(f"✅ Downloaded {file_name} to {output_path}")
            return True

        except requests.exceptions.RequestException as e:
            if self.json_output:
                self.output_json({"error": f"Failed to download file: {e}"})
            else:
                print(f"❌ Failed to download file: {e}")
            return False
        except IOError as e:
            if self.json_output:
                self.output_json({"error": f"Failed to write file: {e}"})
            else:
                print(f"❌ Failed to write file: {e}")
            return False

    def upload_file(self, file_path=None, overwrite=False, folder_id=None, upload_as=None, from_stdin=False):
        """Upload a file to the current folder or specified folder"""
        # If folder_id is provided, use it instead of current_folder
        target_folder_id = folder_id

        if not target_folder_id:
            if not self.current_folder:
                if self.json_output:
                    self.output_json({"error": "No folder selected"})
                else:
                    print("❌ No folder selected.")
                return False
            target_folder_id = self.current_folder['id']

        # Handle stdin upload
        if from_stdin:
            if not upload_as:
                if self.json_output:
                    self.output_json({"error": "When using --stdin, --upload-as must be specified"})
                else:
                    print("❌ When using --stdin, --upload-as must be specified")
                return False

            file_name = upload_as

            if not self.json_output:
                print(f"⬆️ Uploading from stdin as {file_name}...")

            try:
                # Read all data from stdin
                stdin_data = sys.stdin.buffer.read()

                files = {'file': (file_name, stdin_data)}
                data = {
                    'folder_id': str(target_folder_id),
                    'overwrite': str(overwrite).lower()
                }

                response = requests.post(
                    f"{BASE_URL}/storage/api/files",
                    files=files,
                    data=data,
                    headers=self.get_headers()
                )
            except Exception as e:
                if self.json_output:
                    self.output_json({"error": f"Failed to read from stdin: {e}"})
                else:
                    print(f"❌ Failed to read from stdin: {e}")
                return False
        else:
            # Handle regular file upload
            if not file_path:
                if self.json_output:
                    self.output_json({"error": "File path is required when not using stdin"})
                else:
                    print("❌ File path is required when not using stdin")
                return False

            if not os.path.exists(file_path):
                if self.json_output:
                    self.output_json({"error": f"File not found: {file_path}"})
                else:
                    print(f"❌ File not found: {file_path}")
                return False

            # Use custom filename if provided, otherwise use original filename
            file_name = upload_as if upload_as else os.path.basename(file_path)
            original_name = os.path.basename(file_path)

            if not self.json_output:
                if upload_as:
                    print(f"⬆️ Uploading {original_name} as {file_name}...")
                else:
                    print(f"⬆️ Uploading {file_name}...")

            try:
                with open(file_path, 'rb') as f:
                    files = {'file': (file_name, f)}
                    data = {
                        'folder_id': str(target_folder_id),
                        'overwrite': str(overwrite).lower()
                    }

                    response = requests.post(
                        f"{BASE_URL}/storage/api/files",
                        files=files,
                        data=data,
                        headers=self.get_headers()
                    )

            except requests.exceptions.RequestException as e:
                if self.json_output:
                    self.output_json({"error": f"Failed to upload file: {e}"})
                else:
                    print(f"❌ Failed to upload file: {e}")
                return False
            except IOError as e:
                if self.json_output:
                    self.output_json({"error": f"Failed to read file: {e}"})
                else:
                    print(f"❌ Failed to read file: {e}")
                return False

        # Common response handling for both stdin and file uploads
        try:
            if response.status_code == 409:  # Conflict - file exists
                result = response.json()
                if result.get('error') == 'file_exists':
                    if self.json_output:
                        self.output_json({"error": "file_exists", "file_name": file_name})
                        return False
                    else:
                        print(f"❌ A file with the name {file_name} already exists.")
                        if from_stdin:
                            print("❌ Cannot prompt for overwrite when using stdin. Use --overwrite flag.")
                            return False
                        choice = input("Do you want to overwrite it? (y/n): ").lower()
                        if choice == 'y':
                            return self.upload_file(file_path, True, target_folder_id, upload_as, from_stdin)
                        else:
                            print("❌ Upload cancelled.")
                            return False

            if response.status_code not in (200, 201):
                if self.json_output:
                    self.output_json({"error": f"Failed to upload file. Status code: {response.status_code}", "response": response.text})
                else:
                    print(f"❌ Failed to upload file. Status code: {response.status_code}")
                    print(f"Response: {response.text}")
                return False

            result = response.json()
            if self.json_output:
                self.output_json({"success": True, "file": result})
            else:
                print(f"✅ Uploaded {file_name} successfully (ID: {result['id']})")

            # Only refresh if we're using the current folder
            if not folder_id and self.current_folder:
                self.refresh_current_folder()  # Refresh to show the new file
            return True

        except requests.exceptions.RequestException as e:
            if self.json_output:
                self.output_json({"error": f"Failed to upload file: {e}"})
            else:
                print(f"❌ Failed to upload file: {e}")
            return False

    def get_file_info(self, file_index=None, file_id=None):
        """Get detailed information about a file by index or ID"""
        # If file_id is provided, get info by ID
        if file_id:
            try:
                if not self.json_output:
                    print(f"ℹ️ Getting information for file with ID {file_id}...")

                response = requests.get(
                    f"{BASE_URL}/storage/api/files/{file_id}",
                    headers=self.get_headers()
                )

                if response.status_code != 200:
                    if self.json_output:
                        self.output_json({"error": f"Failed to get file info. Status code: {response.status_code}", "response": response.text})
                        return False
                    else:
                        print(f"❌ Failed to get file info. Status code: {response.status_code}")
                        print(f"Response: {response.text}")
                        return False

                file_info = response.json()

                # Check if the file's folder is mounted
                mount_info = self.check_folder_mount(file_info['path'])

                if mount_info:
                    file_info['mount'] = mount_info

                if self.json_output:
                    self.output_json(file_info)
                else:
                    print("\n📄 File Information:")
                    print(f"  ID:           {file_info['id']}")
                    print(f"  Name:         {file_info['name']}")
                    print(f"  Size:         {file_info['size_formatted']} ({file_info['size_bytes']} bytes)")
                    print(f"  Content Type: {file_info['content_type']}")
                    print(f"  Created:      {file_info['created_at']}")
                    print(f"  Updated:      {file_info['updated_at']}")
                    print(f"  Folder ID:    {file_info['folder_id']}")
                    print(f"  Path:         {file_info['path']}")
                    print(f"  ETag:         {file_info['etag']}")
                    print(f"  Download URL: {BASE_URL}{file_info['download_url']}")

                    # Display mount information if available
                    if mount_info:
                        print("\n🔗 Mount:")
                        print(f"  Mount Point:  {mount_info['mount_point']}")
                        print(f"  Local Path:   {mount_info['local_path']}")

                    # Display public links if available
                    if 'public_links' in file_info and file_info['public_links']:
                        print("\n🔗 Public Links:")
                        try:
                            for i, link in enumerate(file_info['public_links'], 1):
                                # Check if link is valid (not expired and not maxed out)
                                is_valid = link.get('is_valid', True)  # Default to True if not provided

                                # If is_valid is not provided, calculate it manually
                                if 'is_valid' not in link:
                                    from datetime import datetime
                                    is_valid = True

                                    # Check expiration
                                    if link.get('expires_at'):
                                        try:
                                            # Parse the expiration date
                                            expires_at = datetime.fromisoformat(link['expires_at'].replace('Z', '+00:00'))
                                            if datetime.now(expires_at.tzinfo) >= expires_at:
                                                is_valid = False
                                        except (ValueError, TypeError):
                                            # If we can't parse the date, assume it's valid
                                            pass

                                    # Check max downloads
                                    if link.get('max_downloads') is not None:
                                        download_count = link.get('download_count', 0)
                                        if download_count >= link['max_downloads']:
                                            is_valid = False

                                # Display link information
                                print(f"  {i}. URL: {link.get('url', link.get('public_url', 'N/A'))}")
                                print(f"     ID: {link.get('id', 'N/A')}")
                                print(f"     Token: {link.get('token', 'N/A')}")
                                print(f"     Created: {link.get('created_at', 'N/A')}")
                                # Show expiration time or "Never" if no expiration
                                if link.get('expires_at'):
                                    print(f"     Expires: {link['expires_at']}")
                                else:
                                    print("     Expires: Never")

                                # Show download count
                                if 'download_count' in link:
                                    print(f"     Downloads: {link['download_count']}")

                                # Show max downloads or "Unlimited" if no limit
                                if 'max_downloads' in link:
                                    if link['max_downloads'] is None:
                                        print("     Max Downloads: Unlimited")
                                    else:
                                        print(f"     Max Downloads: {link['max_downloads']}")

                                # Show status as the last line if link is invalid
                                if not is_valid:
                                    print("     Status: EXPIRED/MAXED OUT")
                                print()
                        except Exception as e:
                            print(f"❌ Error displaying public links: {e}")
                            if self.json_output:
                                print("Public links data:")
                                self.output_json(file_info['public_links'])
                return True
            except requests.exceptions.RequestException as e:
                if self.json_output:
                    self.output_json({"error": f"Failed to get file info: {e}"})
                else:
                    print(f"❌ Failed to get file info: {e}")
                return False

        # Otherwise get info by index
        if not self.current_folder:
            if self.json_output:
                self.output_json({"error": "No folder selected"})
            else:
                print("❌ No folder selected.")
            return False

        if file_index < 1 or file_index > len(self.current_files):
            if self.json_output:
                self.output_json({"error": "Invalid file index"})
            else:
                print("❌ Invalid file index.")
            return False

        file = self.current_files[file_index - 1]
        file_id = file['id']

        # Call the method again with the file ID
        return self.get_file_info(file_id=file_id)

    def create_public_link(self, file_index=None, expires_days=None, max_downloads=None, file_id=None):
        """Create a public link for a file by index or ID"""
        # If file_id is provided, create public link by ID
        if file_id:
            try:
                if not self.json_output:
                    print(f"🔗 Creating public link for file with ID {file_id}...")

                # Prepare the request data
                data = {}
                if expires_days is not None:
                    data['expires_days'] = expires_days
                if max_downloads is not None:
                    data['max_downloads'] = max_downloads

                response = requests.post(
                    f"{BASE_URL}/storage/api/files/{file_id}/public-link",
                    headers=self.get_headers(),
                    json=data
                )

                if response.status_code != 201:
                    if self.json_output:
                        self.output_json({"error": f"Failed to create public link. Status code: {response.status_code}", "response": response.text})
                        return False
                    else:
                        print(f"❌ Failed to create public link. Status code: {response.status_code}")
                        print(f"Response: {response.text}")
                        return False

                result = response.json()

                if self.json_output:
                    self.output_json(result)
                else:
                    print("\n🔗 Public Link Created:")
                    print(f"  URL:           {result['url']}")
                    print(f"  Token:         {result['token']}")
                    if 'expires_at' in result and result['expires_at']:
                        print(f"  Expires:       {result['expires_at']}")
                    if 'max_downloads' in result and result['max_downloads']:
                        print(f"  Max Downloads: {result['max_downloads']}")
                return True

            except requests.exceptions.RequestException as e:
                if self.json_output:
                    self.output_json({"error": f"Failed to create public link: {e}"})
                else:
                    print(f"❌ Failed to create public link: {e}")
                return False

        # Otherwise create by index
        if not self.current_folder:
            if self.json_output:
                self.output_json({"error": "No folder selected"})
            else:
                print("❌ No folder selected.")
            return False

        if file_index < 1 or file_index > len(self.current_files):
            if self.json_output:
                self.output_json({"error": "Invalid file index"})
            else:
                print("❌ Invalid file index.")
            return False

        file = self.current_files[file_index - 1]
        file_id = file['id']
        file_name = file['name']

        if not self.json_output:
            print(f"🔗 Creating public link for {file_name}...")

        # Prepare the request data
        data = {}
        if expires_days is not None:
            data['expires_days'] = expires_days
        if max_downloads is not None:
            data['max_downloads'] = max_downloads

        try:
            response = requests.post(
                f"{BASE_URL}/storage/api/files/{file_id}/public-link",
                headers=self.get_headers(),
                json=data
            )

            if response.status_code != 201:
                if self.json_output:
                    self.output_json({"error": f"Failed to create public link. Status code: {response.status_code}", "response": response.text})
                else:
                    print(f"❌ Failed to create public link. Status code: {response.status_code}")
                    print(f"Response: {response.text}")
                return False

            result = response.json()

            if self.json_output:
                self.output_json(result)
            else:
                print("\n🔗 Public Link Created:")
                print(f"  URL:           {result['url']}")
                print(f"  Token:         {result['token']}")
                if 'expires_at' in result and result['expires_at']:
                    print(f"  Expires:       {result['expires_at']}")
                if 'max_downloads' in result and result['max_downloads']:
                    print(f"  Max Downloads: {result['max_downloads']}")
            return True

        except requests.exceptions.RequestException as e:
            if self.json_output:
                self.output_json({"error": f"Failed to create public link: {e}"})
            else:
                print(f"❌ Failed to create public link: {e}")
            return False

    def delete_public_link(self, link_id):
        """Delete a public link by ID"""
        try:
            if not self.json_output:
                print(f"🗑️ Deleting public link with ID {link_id}...")

            response = requests.delete(
                f"{BASE_URL}/storage/api/public-links/{link_id}",
                headers=self.get_headers()
            )

            if response.status_code != 200:
                if self.json_output:
                    self.output_json({"error": f"Failed to delete public link. Status code: {response.status_code}", "response": response.text})
                    return False
                else:
                    print(f"❌ Failed to delete public link. Status code: {response.status_code}")
                    print(f"Response: {response.text}")
                    return False

            result = response.json()

            if self.json_output:
                self.output_json(result)
            else:
                print("✅ Public link deleted successfully")
            return True

        except requests.exceptions.RequestException as e:
            if self.json_output:
                self.output_json({"error": f"Failed to delete public link: {e}"})
            else:
                print(f"❌ Failed to delete public link: {e}")
            return False

    def delete_used_public_links(self, file_id):
        """Delete all used/expired public links for a file by ID"""
        try:
            if not self.json_output:
                print(f"🗑️ Deleting all used/expired public links for file with ID {file_id}...")

            response = requests.delete(
                f"{BASE_URL}/storage/api/files/{file_id}/public-links/used",
                headers=self.get_headers()
            )

            if response.status_code != 200:
                if self.json_output:
                    self.output_json({"error": f"Failed to delete used public links. Status code: {response.status_code}", "response": response.text})
                    return False
                else:
                    print(f"❌ Failed to delete used public links. Status code: {response.status_code}")
                    print(f"Response: {response.text}")
                    return False

            result = response.json()

            if self.json_output:
                self.output_json(result)
            else:
                print(f"✅ {result.get('message', 'Used public links deleted successfully')}")
            return True

        except requests.exceptions.RequestException as e:
            if self.json_output:
                self.output_json({"error": f"Failed to delete used public links: {e}"})
            else:
                print(f"❌ Failed to delete used public links: {e}")
            return False

    def print_help(self):
        """Print help information"""
        print("\n📚 Available commands:")
        print("  ls                      - List contents of current folder")
        print("  cd <subfolder_index>    - Enter a subfolder")
        print("  back                    - Go back to parent folder")
        print("  home                    - Go back to folder selection (deselect current folder)")
        print("  mkdir <folder_name>     - Create a new folder (supports nested paths like 'a/b/c')")
        print("  rm <file_index>         - Delete a file")
        print("  rmdir <subfolder_index> - Delete a subfolder")
        print("  folders                 - List all accessible folders")
        print("  select <folder_index>   - Select a folder from the accessible folders list")
        print("  download <file_index>   - Download a file")
        print("  upload <file_path>      - Upload a file to current folder")
        print("  info <file_index>       - Get detailed information about a file")
        print("  public <file_index> [expires_days] [max_downloads] - Create a public link for a file")
        print("  delete-link <link_id>   - Delete a specific public link by ID")
        print("  delete-used <file_id>   - Delete all expired/maxed out public links for a file")
        print("  token <token>           - Set API token for authentication")
        print("  help                    - Show this help message")
        print("  exit                    - Exit the program")

    def run(self):
        """Run the CLI"""
        self.initialize()
        self.list_accessible_folders()

        print("\nPlease select a folder to start browsing (e.g., 'select 1').")
        self.print_help()

        while True:
            try:
                command = input("\n> ").strip()

                if not command:
                    continue

                parts = command.split()
                cmd = parts[0].lower()

                if cmd == 'exit':
                    print("👋 Goodbye!")
                    break

                elif cmd == 'help':
                    self.print_help()

                elif cmd == 'token':
                    if len(parts) < 2:
                        print("❌ Please specify a token (e.g., 'token your-api-token').")
                        continue

                    self.token = parts[1]
                    print("✅ Token set successfully.")

                    # Ask if user wants to save the token
                    save_token = input("Do you want to save this token to the config file? (y/n): ").lower().strip()
                    if save_token == 'y':
                        if save_config(self.token):
                            print(f"✅ Token saved to {CONFIG_PATH}")
                        else:
                            print(f"❌ Failed to save token to {CONFIG_PATH}")

                elif cmd == 'folders':
                    self.list_accessible_folders()

                elif cmd == 'select':
                    if len(parts) < 2:
                        print("❌ Please specify a folder index (e.g., 'select 1').")
                        continue

                    try:
                        folder_index = int(parts[1])
                        if self.select_folder(folder_index):
                            self.display_current_folder()
                    except ValueError:
                        print("❌ Invalid folder index. Please enter a number.")

                elif cmd == 'ls':
                    if not self.current_folder:
                        print("❌ No folder selected. Use 'select <folder_index>' to select a folder.")
                        continue

                    self.display_current_folder()

                elif cmd == 'cd':
                    if not self.current_folder:
                        print("❌ No folder selected. Use 'select <folder_index>' to select a folder.")
                        continue

                    if len(parts) < 2:
                        print("❌ Please specify a subfolder index (e.g., 'cd 1').")
                        continue

                    try:
                        subfolder_index = int(parts[1])
                        if self.enter_subfolder(subfolder_index):
                            self.display_current_folder()
                    except ValueError:
                        print("❌ Invalid subfolder index. Please enter a number.")

                elif cmd == 'back':
                    if not self.current_folder:
                        print("❌ No folder selected. Use 'select <folder_index>' to select a folder.")
                        continue

                    if self.go_back():
                        self.display_current_folder()

                elif cmd == 'home':
                    # Go back to folder selection (deselect current folder)
                    self.current_folder = None
                    self.folder_stack = []
                    self.current_files = []
                    self.current_subfolders = []
                    print("🏠 Returned to folder selection")
                    self.list_accessible_folders()
                    print("\nPlease select a folder to start browsing (e.g., 'select 1').")
                elif cmd == 'mkdir':
                    if not self.current_folder:
                        print("❌ No folder selected. Use 'select <folder_index>' to select a folder.")
                        continue

                    if len(parts) < 2:
                        print("❌ Usage: mkdir <folder_name> or mkdir <path/to/nested/folders>")
                        continue

                    folder_path = ' '.join(parts[1:])  # Support folder names with spaces

                    # Validate folder path
                    if not folder_path.strip():
                        print("❌ Folder path cannot be empty")
                        continue

                    # Check if this is a nested path (contains '/')
                    if '/' in folder_path:
                        # Create nested folder hierarchy
                        path_parts = [part.strip() for part in folder_path.split('/') if part.strip()]
                        current_parent_id = self.current_folder['id']
                        created_folders = []

                        try:
                            for folder_name in path_parts:
                                # Check if this folder already exists at this level
                                response = requests.get(
                                    f"{BASE_URL}/storage/api/folders?parent_id={current_parent_id}",
                                    headers=self.get_headers()
                                )

                                if response.status_code == 200:
                                    existing_folders = response.json()
                                    existing_folder = None
                                    for folder in existing_folders:
                                        if folder['name'] == folder_name:
                                            existing_folder = folder
                                            break

                                    if existing_folder:
                                        # Folder exists, use its ID as parent for next level
                                        current_parent_id = existing_folder['id']
                                    else:
                                        # Create the folder
                                        new_folder = self.create_folder(folder_name, current_parent_id, silent=True)
                                        if new_folder:
                                            created_folders.append(folder_name)
                                            current_parent_id = new_folder['id']
                                        else:
                                            print(f"❌ Failed to create folder '{folder_name}' in path '{folder_path}'")
                                            return
                                else:
                                    print(f"❌ Failed to check existing folders at level '{folder_name}'")
                                    return

                            if created_folders:
                                if len(created_folders) == len(path_parts):
                                    print(f"✅ Created folder hierarchy: {folder_path}")
                                else:
                                    existing_count = len(path_parts) - len(created_folders)
                                    print(f"✅ Created folders: {' -> '.join(created_folders)} ({existing_count} already existed)")
                            else:
                                print(f"📁 All folders in path '{folder_path}' already exist")

                        except Exception as e:
                            print(f"❌ Error creating folder hierarchy: {e}")
                    else:
                        # Single folder creation (original behavior)
                        folder_name = folder_path

                        # Check if folder already exists
                        if self.current_subfolders:
                            existing_folders = [folder['name'] for folder in self.current_subfolders]
                            if folder_name in existing_folders:
                                print(f"❌ Folder '{folder_name}' already exists")
                                continue

                        # Create the folder
                        try:
                            new_folder = self.create_folder(folder_name, self.current_folder['id'], silent=True)
                            if new_folder:
                                print(f"✅ Created folder '{folder_name}'")
                            else:
                                print(f"❌ Failed to create folder '{folder_name}'")
                        except Exception as e:
                            print(f"❌ Error creating folder: {e}")

                    # Refresh current folder and accessible folders list after any creation
                    try:
                        self.refresh_current_folder()
                        response = requests.get(
                            f"{BASE_URL}/storage/api/accessible-folders",
                            headers=self.get_headers()
                        )
                        if response.status_code == 200:
                            self.accessible_folders = response.json()
                    except Exception:
                        pass  # Don't fail if we can't refresh the list

                elif cmd == 'download':
                    if not self.current_folder:
                        print("❌ No folder selected. Use 'select <folder_index>' to select a folder.")
                        continue

                    if len(parts) < 2:
                        print("❌ Please specify a file index (e.g., 'download 1').")
                        continue

                    try:
                        file_index = int(parts[1])
                        output_path = parts[2] if len(parts) > 2 else None
                        self.download_file(file_index, output_path)
                    except ValueError:
                        print("❌ Invalid file index. Please enter a number.")

                elif cmd == 'rm':
                    if not self.current_folder:
                        print("❌ No folder selected. Use 'select <folder_index>' to select a folder.")
                        continue

                    if len(parts) < 2:
                        print("❌ Please specify a file index (e.g., 'rm 1').")
                        continue

                    try:
                        file_index = int(parts[1])
                        if file_index < 1 or file_index > len(self.current_files):
                            print("❌ Invalid file index.")
                            continue

                        file = self.current_files[file_index - 1]
                        file_name = file['name']
                        file_id = file['id']

                        # Confirm deletion
                        confirm = input(f"Are you sure you want to delete '{file_name}'? (y/N): ").lower().strip()
                        if confirm == 'y':
                            if self.delete_file(file_id):
                                # Refresh current folder to update file list
                                self.refresh_current_folder()
                        else:
                            print("❌ File deletion cancelled.")
                    except ValueError:
                        print("❌ Invalid file index. Please enter a number.")

                elif cmd == 'rmdir':
                    if not self.current_folder:
                        print("❌ No folder selected. Use 'select <folder_index>' to select a folder.")
                        continue

                    if len(parts) < 2:
                        print("❌ Please specify a subfolder index (e.g., 'rmdir 1').")
                        continue

                    try:
                        subfolder_index = int(parts[1])
                        if subfolder_index < 1 or subfolder_index > len(self.current_subfolders):
                            print("❌ Invalid subfolder index.")
                            continue

                        subfolder = self.current_subfolders[subfolder_index - 1]
                        subfolder_name = subfolder['name']
                        subfolder_id = subfolder['id']

                        # Confirm deletion
                        confirm = input(f"Are you sure you want to delete folder '{subfolder_name}' and all its contents? (y/N): ").lower().strip()
                        if confirm == 'y':
                            if self.delete_folder(subfolder_id):
                                # Refresh current folder to update subfolder list
                                self.refresh_current_folder()
                                # Refresh accessible folders list
                                try:
                                    response = requests.get(
                                        f"{BASE_URL}/storage/api/accessible-folders",
                                        headers=self.get_headers()
                                    )
                                    if response.status_code == 200:
                                        self.accessible_folders = response.json()
                                except Exception:
                                    pass  # Don't fail if we can't refresh the list
                        else:
                            print("❌ Folder deletion cancelled.")
                    except ValueError:
                        print("❌ Invalid subfolder index. Please enter a number.")

                elif cmd == 'upload':
                    if not self.current_folder:
                        print("❌ No folder selected. Use 'select <folder_index>' to select a folder.")
                        continue

                    if len(parts) < 2:
                        print("❌ Please specify a file path (e.g., 'upload /path/to/file.txt').")
                        continue

                    file_path = ' '.join(parts[1:])  # Join all parts after 'upload' to handle paths with spaces
                    self.upload_file(file_path)

                elif cmd == 'info':
                    if not self.current_folder:
                        print("❌ No folder selected. Use 'select <folder_index>' to select a folder.")
                        continue

                    if len(parts) < 2:
                        print("❌ Please specify a file index (e.g., 'info 1').")
                        continue

                    try:
                        file_index = int(parts[1])
                        self.get_file_info(file_index)
                    except ValueError:
                        print("❌ Invalid file index. Please enter a number.")

                elif cmd == 'public':
                    if not self.current_folder:
                        print("❌ No folder selected. Use 'select <folder_index>' to select a folder.")
                        continue

                    if len(parts) < 2:
                        print("❌ Please specify a file index (e.g., 'public 1').")
                        continue

                    try:
                        file_index = int(parts[1])
                        expires_days = None
                        max_downloads = None

                        # Check for optional expires_days parameter
                        if len(parts) >= 3:
                            try:
                                expires_days = int(parts[2])
                            except ValueError:
                                print("❌ Invalid expires_days. Please enter a number.")
                                continue

                        # Check for optional max_downloads parameter
                        if len(parts) >= 4:
                            try:
                                max_downloads = int(parts[3])
                            except ValueError:
                                print("❌ Invalid max_downloads. Please enter a number.")
                                continue

                        self.create_public_link(file_index, expires_days, max_downloads)
                    except ValueError:
                        print("❌ Invalid file index. Please enter a number.")

                elif cmd == 'delete-link':
                    if len(parts) < 2:
                        print("❌ Please specify a link ID (e.g., 'delete-link 123').")
                        continue

                    try:
                        link_id = int(parts[1])
                        self.delete_public_link(link_id)
                    except ValueError:
                        print("❌ Invalid link ID. Please enter a number.")

                elif cmd == 'delete-used':
                    if len(parts) < 2:
                        print("❌ Please specify a file ID (e.g., 'delete-used 456').")
                        continue

                    try:
                        file_id = int(parts[1])
                        self.delete_used_public_links(file_id)
                    except ValueError:
                        print("❌ Invalid file ID. Please enter a number.")

                else:
                    print(f"❌ Unknown command: {cmd}")
                    print("Type 'help' to see available commands.")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ An error occurred: {e}")

    def get_folder_by_id(self, folder_id):
        """Get a folder by ID"""
        try:
            response = requests.get(
                f"{BASE_URL}/storage/api/folders/{folder_id}",
                headers=self.get_headers()
            )

            if response.status_code != 200:
                if self.json_output:
                    self.output_json({"error": f"Failed to get folder. Status code: {response.status_code}", "response": response.text})
                else:
                    print(f"❌ Failed to get folder. Status code: {response.status_code}")
                    print(f"Response: {response.text}")
                return None

            folder = response.json()
            return folder

        except requests.exceptions.RequestException as e:
            if self.json_output:
                self.output_json({"error": f"Failed to get folder: {e}"})
            else:
                print(f"❌ Failed to get folder: {e}")
            return None

    def check_folder_mount(self, file_path):
        """
        Check if the file is directly accessible in the container
        through a mounted folder under /objects/
        """
        # Construct the potential local path
        local_path = f"/objects/{file_path}"

        # Check if the file exists at this path
        if os.path.exists(local_path):
            # The mount point should be a directory, not the file itself
            # Start with /objects and work our way down to find the mount point

            # Get the mount information
            # Try to get mount information from /proc/mounts
            try:
                with open('/proc/mounts', 'r') as f:
                    mount_lines = f.readlines()

                # Find all mounts under /objects/
                object_mounts = []
                for line in mount_lines:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1].startswith('/objects/'):
                        object_mounts.append(parts[1])

                # Sort mount points by length (descending) to find the most specific match first
                object_mounts.sort(key=len, reverse=True)

                # Find the most specific mount point that contains this file
                for mount_point in object_mounts:
                    if local_path.startswith(mount_point + '/') or local_path == mount_point:
                        return {
                            "local_path": local_path,
                            "mount_point": mount_point
                        }

                # If we couldn't find a specific mount point from /proc/mounts,
                # use /objects as the default mount point
                return {
                    "local_path": local_path,
                    "mount_point": "/objects"
                }

            except Exception:
                # If we can't read /proc/mounts, just use /objects as the mount point
                return {
                    "local_path": local_path,
                    "mount_point": "/objects"
                }

        return None

    def resolve_file_path(self, file_path):
        """
        Resolve a file path like 'Default/test/myfile.txt' to find the file ID.
        Returns the file ID if found, None otherwise.
        """
        if not file_path:
            return None

        # Split the path into components
        path_parts = file_path.strip('/').split('/')
        if not path_parts:
            return None

        # The first part should be a root folder name
        root_folder_name = path_parts[0]

        # Find the root folder by name
        root_folder = None
        for folder in self.accessible_folders:
            if folder['name'] == root_folder_name:
                # Check if this is a root folder (no parent or parent not accessible)
                parent_id = folder.get('parent_id')
                if parent_id is None:
                    root_folder = folder
                    break
                else:
                    # Check if parent is in accessible folders
                    parent_exists = any(f['id'] == parent_id for f in self.accessible_folders)
                    if not parent_exists:
                        root_folder = folder
                        break

        if not root_folder:
            if not self.json_output:
                print(f"❌ Root folder '{root_folder_name}' not found or not accessible")
            return None

        # If the path only has one component, we're looking for a file in the root folder
        if len(path_parts) == 1:
            if not self.json_output:
                print(f"❌ Path '{file_path}' appears to be a folder, not a file")
            return None

        # Navigate through the folder hierarchy
        current_folder_id = root_folder['id']

        # Process intermediate folders (all but the last component which should be the file)
        for folder_name in path_parts[1:-1]:
            # Get subfolders of current folder
            try:
                response = requests.get(
                    f"{BASE_URL}/storage/api/folders?parent_id={current_folder_id}",
                    headers=self.get_headers()
                )

                if response.status_code != 200:
                    if not self.json_output:
                        print(f"❌ Failed to get subfolders. Status code: {response.status_code}")
                    return None

                subfolders = response.json()

                # Find the subfolder with the matching name
                target_folder = None
                for subfolder in subfolders:
                    if subfolder['name'] == folder_name:
                        target_folder = subfolder
                        break

                if not target_folder:
                    if not self.json_output:
                        print(f"❌ Folder '{folder_name}' not found in path '{file_path}'")
                    return None

                current_folder_id = target_folder['id']

            except requests.exceptions.RequestException as e:
                if not self.json_output:
                    print(f"❌ Failed to navigate folder hierarchy: {e}")
                return None

        # Now look for the file in the final folder
        file_name = path_parts[-1]

        try:
            response = requests.get(
                f"{BASE_URL}/storage/api/files?folder_id={current_folder_id}",
                headers=self.get_headers()
            )

            if response.status_code != 200:
                if not self.json_output:
                    print(f"❌ Failed to get files. Status code: {response.status_code}")
                return None

            files = response.json()

            # Find the file with the matching name
            for file in files:
                if file['name'] == file_name:
                    return file['id']

            if not self.json_output:
                print(f"❌ File '{file_name}' not found in path '{file_path}'")
            return None

        except requests.exceptions.RequestException as e:
            if not self.json_output:
                print(f"❌ Failed to search for file: {e}")
            return None

    def create_folder(self, folder_name, parent_id=None, silent=False):
        """
        Create a new folder using the API.
        Returns the created folder data if successful, None otherwise.
        If silent=True, suppresses success messages (useful for interactive commands that print their own messages).
        """
        try:
            data = {
                'name': folder_name
            }
            if parent_id:
                data['parent_id'] = parent_id

            response = requests.post(
                f"{BASE_URL}/storage/api/folders",
                headers=self.get_headers(),
                json=data
            )

            if response.status_code == 201:
                folder_data = response.json()
                if not self.json_output and not silent:
                    print(f"✅ Created folder: {folder_name}")
                return folder_data
            else:
                if not self.json_output:
                    print(f"❌ Failed to create folder '{folder_name}'. Status code: {response.status_code}")
                    print(f"Response: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            if not self.json_output:
                print(f"❌ Failed to create folder '{folder_name}': {e}")
            return None

    def delete_file(self, file_id):
        """
        Delete a file using the API.
        Returns True if successful, False otherwise.
        """
        try:
            response = requests.delete(
                f"{BASE_URL}/storage/api/files/{file_id}",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                if not self.json_output:
                    print("✅ File deleted successfully")
                return True
            else:
                if not self.json_output:
                    print(f"❌ Failed to delete file. Status code: {response.status_code}")
                    print(f"Response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            if not self.json_output:
                print(f"❌ Failed to delete file: {e}")
            return False

    def delete_folder(self, folder_id):
        """
        Delete a folder using the API.
        Returns True if successful, False otherwise.
        """
        try:
            response = requests.delete(
                f"{BASE_URL}/storage/api/folders/{folder_id}",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                if not self.json_output:
                    print("✅ Folder deleted successfully")
                return True
            else:
                if not self.json_output:
                    print(f"❌ Failed to delete folder. Status code: {response.status_code}")
                    print(f"Response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            if not self.json_output:
                print(f"❌ Failed to delete folder: {e}")
            return False

    def resolve_folder_path(self, folder_path, create_missing=False):
        """
        Resolve a folder path like 'Default/test' to find the folder ID.
        Path must start with a root folder name, followed by subfolders.
        If create_missing is True, creates missing folders in the path.
        Returns the folder ID if found/created, None otherwise.
        """
        if not folder_path:
            return None

        # Split the path into components
        path_parts = folder_path.strip('/').split('/')
        if not path_parts:
            return None

        # The first part must be a root folder name
        root_folder_name = path_parts[0]

        # Find the root folder by name
        root_folder = None
        for folder in self.accessible_folders:
            if folder['name'] == root_folder_name:
                # Check if this is a root folder (no parent or parent not accessible)
                parent_id = folder.get('parent_id')
                if parent_id is None:
                    root_folder = folder
                    break
                else:
                    # Check if parent is in accessible folders
                    parent_exists = any(f['id'] == parent_id for f in self.accessible_folders)
                    if not parent_exists:
                        root_folder = folder
                        break

        if not root_folder:
            if not self.json_output:
                print(f"❌ Root folder '{root_folder_name}' not found or not accessible")
            return None

        # If the path only has one component, return the root folder ID
        if len(path_parts) == 1:
            return root_folder['id']

        # Navigate through the folder hierarchy
        current_folder_id = root_folder['id']

        # Process all folder components
        for folder_name in path_parts[1:]:
            # Get subfolders of current folder
            try:
                response = requests.get(
                    f"{BASE_URL}/storage/api/folders?parent_id={current_folder_id}",
                    headers=self.get_headers()
                )

                if response.status_code != 200:
                    if not self.json_output:
                        print(f"❌ Failed to get subfolders. Status code: {response.status_code}")
                    return None

                subfolders = response.json()

                # Find the subfolder with the matching name
                target_folder = None
                for subfolder in subfolders:
                    if subfolder['name'] == folder_name:
                        target_folder = subfolder
                        break

                if not target_folder:
                    if create_missing:
                        # Create the missing folder
                        if not self.json_output:
                            print(f"📁 Creating missing folder: {folder_name}")
                        created_folder = self.create_folder(folder_name, current_folder_id)
                        if created_folder:
                            current_folder_id = created_folder['id']
                        else:
                            if not self.json_output:
                                print(f"❌ Failed to create folder '{folder_name}' in path '{folder_path}'")
                            return None
                    else:
                        if not self.json_output:
                            print(f"❌ Folder '{folder_name}' not found in path '{folder_path}'")
                        return None
                else:
                    current_folder_id = target_folder['id']

            except requests.exceptions.RequestException as e:
                if not self.json_output:
                    print(f"❌ Failed to navigate folder hierarchy: {e}")
                return None

        return current_folder_id

    def browse_folder(self, folder_id):
        """Browse a folder by ID"""
        folder = self.get_folder_by_id(folder_id)
        if not folder:
            return False

        self.current_folder = folder
        self.folder_stack = [folder]  # Reset folder stack
        if self.refresh_current_folder():
            self.display_current_folder()
            return True
        return False

    def calculate_local_etag(self, file_path):
        """
        Calculate MD5 hash of a local file using the same method as the server.
        This ensures local and remote ETags are directly comparable.

        Args:
            file_path: Path to the local file

        Returns:
            MD5 hash as hexadecimal string (matches server ETag format)
        """
        file_hash = hashlib.md5()  # nosec - used for content comparison, not security

        with open(file_path, 'rb') as f:
            # Read in 4KB chunks (same as server)
            for chunk in iter(lambda: f.read(4096), b""):
                file_hash.update(chunk)

        return file_hash.hexdigest()

    def _get_remote_file_tree(self, folder_id, base_path=""):
        """
        Recursively get all files in a folder and its subfolders.

        Args:
            folder_id: ID of the folder to scan
            base_path: Base path for building relative paths

        Returns:
            Tuple of (files_dict, folders_dict) where:
            - files_dict maps relative paths to file info
            - folders_dict maps relative paths to folder info
        """
        files_result = {}
        folders_result = {}

        try:
            # Get files in current folder
            response = requests.get(
                f"{BASE_URL}/storage/api/files?folder_id={folder_id}",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                files = response.json()
                if files:  # Check if files is not None
                    for file_info in files:
                        relative_path = os.path.join(base_path, file_info['name']) if base_path else file_info['name']
                        files_result[relative_path] = {
                            'id': file_info['id'],
                            'etag': file_info['etag'],
                            'size_bytes': file_info['size_bytes']
                        }

            # Get subfolders
            response = requests.get(
                f"{BASE_URL}/storage/api/folders?parent_id={folder_id}",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                subfolders = response.json()
                if subfolders:  # Check if subfolders is not None
                    for subfolder in subfolders:
                        subfolder_path = os.path.join(base_path, subfolder['name']) if base_path else subfolder['name']
                        # Track this folder
                        folders_result[subfolder_path] = {
                            'id': subfolder['id'],
                            'parent_id': folder_id
                        }
                        # Recursively get files and folders from subfolder
                        subfolder_files, subfolder_folders = self._get_remote_file_tree(subfolder['id'], subfolder_path)
                        files_result.update(subfolder_files)
                        folders_result.update(subfolder_folders)

        except requests.exceptions.RequestException as e:
            if not self.json_output:
                print(f"⚠️ Warning: Failed to scan remote folder {folder_id}: {e}")

        return files_result, folders_result

    def _scan_local_directory(self, local_path):
        """
        Recursively scan a local directory and build a file tree.

        Args:
            local_path: Path to the local directory

        Returns:
            Tuple of (files_dict, folders_set) where:
            - files_dict maps relative paths to file info
            - folders_set contains all folder paths
        """
        files_result = {}
        folders_result = set()

        for root, _dirs, files in os.walk(local_path):
            # Track folder path
            if root != local_path:
                relative_dir = os.path.relpath(root, local_path).replace(os.sep, '/')
                folders_result.add(relative_dir)

            for filename in files:
                full_path = os.path.join(root, filename)
                relative_path = os.path.relpath(full_path, local_path)

                # Normalize path separators for cross-platform compatibility
                relative_path = relative_path.replace(os.sep, '/')

                try:
                    size = os.path.getsize(full_path)
                    files_result[relative_path] = {
                        'size': size,
                        'full_path': full_path,
                        'md5': None  # Will be calculated only if needed
                    }
                except OSError as e:
                    if not self.json_output:
                        print(f"⚠️ Warning: Cannot access {full_path}: {e}")

        return files_result, folders_result

    def sync_directory(self, local_path, remote_folder_id, delete=False, dry_run=False):
        """
        Sync a local directory to a remote folder (rsync-like behavior).

        Args:
            local_path: Local directory path to sync from
            remote_folder_id: Remote folder ID to sync to
            delete: If True, delete remote files not in local (like rsync --delete)
            dry_run: If True, show what would be done without doing it

        Returns:
            Dict with sync statistics
        """
        if not self.json_output:
            print(f"\n🔄 Syncing local directory: {local_path}")
            print(f"   To remote folder ID: {remote_folder_id}")
            if delete:
                print("   Mode: Mirror (--delete enabled)")
            else:
                print("   Mode: Upload new/modified files only")
            if dry_run:
                print("   🔍 DRY RUN - No changes will be made")
            print()

        # Get remote folder info
        remote_folder = self.get_folder_by_id(remote_folder_id)
        if not remote_folder:
            return {'error': 'Remote folder not found'}

        # Scan local directory
        if not self.json_output:
            print("📂 Scanning local directory...")
        local_files, local_folders = self._scan_local_directory(local_path)
        if not self.json_output:
            print(f"   Found {len(local_files)} local file(s) in {len(local_folders)} folder(s)")

        # Scan remote folder
        if not self.json_output:
            print("☁️  Scanning remote folder...")
        remote_files, remote_folders = self._get_remote_file_tree(remote_folder_id)
        if not self.json_output:
            print(f"   Found {len(remote_files)} remote file(s) in {len(remote_folders)} folder(s)")

        # Compare and determine actions
        if not self.json_output:
            print("\n🔍 Analyzing differences...")

        actions = []
        folders_to_create = set()

        # Check each local file
        for local_path_rel, local_info in local_files.items():
            if local_path_rel in remote_files:
                remote_info = remote_files[local_path_rel]

                # Always compare using MD5/ETag checksums
                if local_info['md5'] is None:
                    local_info['md5'] = self.calculate_local_etag(local_info['full_path'])

                if local_info['md5'] != remote_info['etag']:
                    actions.append({
                        'action': 'upload',
                        'path': local_path_rel,
                        'reason': 'content_changed',
                        'local_path': local_info['full_path']
                    })
                else:
                    # File is identical
                    actions.append({
                        'action': 'skip',
                        'path': local_path_rel,
                        'reason': 'unchanged'
                    })

                # Mark as seen
                remote_files[local_path_rel]['seen'] = True
            else:
                # New file
                actions.append({
                    'action': 'upload',
                    'path': local_path_rel,
                    'reason': 'new',
                    'local_path': local_info['full_path']
                })

                # Track folders that need to be created
                dir_path = os.path.dirname(local_path_rel)
                if dir_path:
                    folders_to_create.add(dir_path)

        # Handle deletions if --delete flag is set
        folders_to_delete = []
        if delete:
            # Delete files not in local
            for remote_path, remote_info in remote_files.items():
                if not remote_info.get('seen'):
                    actions.append({
                        'action': 'delete',
                        'path': remote_path,
                        'file_id': remote_info['id'],
                        'reason': 'not_in_local'
                    })

            # Delete folders not in local (must be done after files are deleted)
            for remote_folder_path, remote_folder_info in remote_folders.items():
                if remote_folder_path not in local_folders:
                    folders_to_delete.append({
                        'path': remote_folder_path,
                        'folder_id': remote_folder_info['id']
                    })

        # Execute or display actions
        stats = self._execute_sync_actions(
            actions,
            folders_to_create,
            folders_to_delete,
            remote_folder_id,
            local_path,
            dry_run
        )

        return stats

    def _execute_sync_actions(self, actions, folders_to_create, folders_to_delete, remote_folder_id, local_base_path, dry_run):
        """
        Execute or display sync actions.

        Args:
            actions: List of action dicts
            folders_to_create: Set of folder paths that need to be created
            folders_to_delete: List of folder dicts to delete
            remote_folder_id: ID of the remote root folder
            local_base_path: Base path of local directory
            dry_run: If True, only display actions without executing

        Returns:
            Dict with statistics
        """
        stats = {
            'uploaded': 0,
            'deleted': 0,
            'skipped': 0,
            'errors': 0,
            'folders_created': 0,
            'folders_deleted': 0
        }

        # Count actions
        upload_actions = [a for a in actions if a['action'] == 'upload']
        delete_actions = [a for a in actions if a['action'] == 'delete']
        skip_actions = [a for a in actions if a['action'] == 'skip']

        if not self.json_output:
            print("\n📊 Summary:")
            print(f"   Files to upload: {len(upload_actions)}")
            print(f"   Files to delete: {len(delete_actions)}")
            print(f"   Files unchanged: {len(skip_actions)}")
            print(f"   Folders to create: {len(folders_to_create)}")
            print(f"   Folders to delete: {len(folders_to_delete)}")
            print()

        if dry_run:
            if not self.json_output:
                print("🔍 DRY RUN - Actions that would be performed:\n")

                if folders_to_create:
                    print("📁 Folders to create:")
                    for folder_path in sorted(folders_to_create):
                        print(f"   + {folder_path}/")
                    print()

                if upload_actions:
                    print("⬆️  Files to upload:")
                    for action in upload_actions:
                        reason_str = f"({action['reason']})" if action['reason'] != 'new' else "(new)"
                        print(f"   + {action['path']} {reason_str}")
                    print()

                if delete_actions:
                    print("🗑️  Files to delete:")
                    for action in delete_actions:
                        print(f"   - {action['path']}")
                    print()

                if folders_to_delete:
                    print("📁 Folders to delete:")
                    for folder_info in sorted(folders_to_delete, key=lambda x: x['path'], reverse=True):
                        print(f"   - {folder_info['path']}/")
                    print()

            return stats

        # Execute actions
        if not self.json_output and (upload_actions or delete_actions or folders_to_create or folders_to_delete):
            print("🚀 Executing sync...\n")

        # Create folders first
        folder_id_map = {'.': remote_folder_id}  # Map relative paths to folder IDs

        if folders_to_create:
            if not self.json_output:
                print("📁 Creating folders...")

            for folder_path in sorted(folders_to_create):
                parts = folder_path.split('/')
                current_path = ''
                parent_id = remote_folder_id

                for part in parts:
                    current_path = os.path.join(current_path, part) if current_path else part
                    current_path_normalized = current_path.replace(os.sep, '/')

                    if current_path_normalized not in folder_id_map:
                        # Check if folder exists
                        try:
                            response = requests.get(
                                f"{BASE_URL}/storage/api/folders?parent_id={parent_id}",
                                headers=self.get_headers()
                            )

                            if response.status_code == 200:
                                existing_folders = response.json()
                                existing_folder = None
                                if existing_folders:  # Check if not None
                                    for folder in existing_folders:
                                        if folder['name'] == part:
                                            existing_folder = folder
                                            break

                                if existing_folder:
                                    folder_id_map[current_path_normalized] = existing_folder['id']
                                    parent_id = existing_folder['id']
                                else:
                                    # Create folder
                                    created_folder = self.create_folder(part, parent_id, silent=True)
                                    if created_folder:
                                        folder_id_map[current_path_normalized] = created_folder['id']
                                        parent_id = created_folder['id']
                                        stats['folders_created'] += 1
                                        if not self.json_output:
                                            print(f"   ✅ Created: {current_path_normalized}/")
                                    else:
                                        stats['errors'] += 1
                                        if not self.json_output:
                                            print(f"   ❌ Failed to create: {current_path_normalized}/")
                                        break
                        except Exception as e:
                            stats['errors'] += 1
                            if not self.json_output:
                                print(f"   ❌ Error creating {current_path_normalized}/: {e}")
                            break

            if not self.json_output:
                print()

        # Upload files
        if upload_actions:
            if not self.json_output:
                print("⬆️  Uploading files...")

            for i, action in enumerate(upload_actions, 1):
                file_path = action['path']
                local_file_path = action['local_path']

                # Determine target folder ID
                dir_path = os.path.dirname(file_path)
                dir_path_normalized = dir_path.replace(os.sep, '/') if dir_path else '.'
                target_folder_id = folder_id_map.get(dir_path_normalized, remote_folder_id)

                # Upload file
                try:
                    if self.upload_file(local_file_path, overwrite=True, folder_id=target_folder_id):
                        stats['uploaded'] += 1
                        if not self.json_output:
                            progress = f"[{i}/{len(upload_actions)}]"
                            reason_str = f"({action['reason']})" if action['reason'] != 'new' else "(new)"
                            print(f"   {progress} ✅ {file_path} {reason_str}")
                    else:
                        stats['errors'] += 1
                        if not self.json_output:
                            print(f"   ❌ Failed: {file_path}")
                except Exception as e:
                    stats['errors'] += 1
                    if not self.json_output:
                        print(f"   ❌ Error uploading {file_path}: {e}")

            if not self.json_output:
                print()

        # Delete files
        if delete_actions:
            if not self.json_output:
                print("🗑️  Deleting files...")

            for i, action in enumerate(delete_actions, 1):
                file_path = action['path']
                file_id = action['file_id']

                try:
                    if self.delete_file(file_id):
                        stats['deleted'] += 1
                        if not self.json_output:
                            progress = f"[{i}/{len(delete_actions)}]"
                            print(f"   {progress} ✅ Deleted: {file_path}")
                    else:
                        stats['errors'] += 1
                        if not self.json_output:
                            print(f"   ❌ Failed to delete: {file_path}")
                except Exception as e:
                    stats['errors'] += 1
                    if not self.json_output:
                        print(f"   ❌ Error deleting {file_path}: {e}")

            if not self.json_output:
                print()

        # Delete empty folders (must be done after files are deleted, in reverse order)
        if folders_to_delete:
            if not self.json_output:
                print("📁 Deleting empty folders...")

            # Sort by path depth (deepest first) to delete children before parents
            folders_to_delete_sorted = sorted(folders_to_delete, key=lambda x: x['path'].count('/'), reverse=True)

            for i, folder_info in enumerate(folders_to_delete_sorted, 1):
                folder_path = folder_info['path']
                folder_id = folder_info['folder_id']

                try:
                    if self.delete_folder(folder_id):
                        stats['folders_deleted'] += 1
                        if not self.json_output:
                            progress = f"[{i}/{len(folders_to_delete_sorted)}]"
                            print(f"   {progress} ✅ Deleted: {folder_path}/")
                    else:
                        stats['errors'] += 1
                        if not self.json_output:
                            print(f"   ❌ Failed to delete: {folder_path}/")
                except Exception as e:
                    stats['errors'] += 1
                    if not self.json_output:
                        print(f"   ❌ Error deleting {folder_path}/: {e}")

            if not self.json_output:
                print()

        stats['skipped'] = len(skip_actions)

        # Final summary
        if not self.json_output:
            print("✨ Sync complete!")
            print("\n📊 Results:")
            print(f"   Folders created: {stats['folders_created']}")
            print(f"   Folders deleted: {stats['folders_deleted']}")
            print(f"   Files uploaded: {stats['uploaded']}")
            print(f"   Files deleted: {stats['deleted']}")
            print(f"   Files unchanged: {stats['skipped']}")
            if stats['errors'] > 0:
                print(f"   ⚠️  Errors: {stats['errors']}")

        return stats

def main():
    parser = argparse.ArgumentParser(description='Container Storage CLI')
    parser.add_argument('--url', help='Storage API URL (default: http://localhost:5000 or STORAGE_API_URL env var)')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    parser.add_argument('--token', help='API token for authentication')

    # Add command-line flags for operations
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--configure', action='store_true', help='Configure API token and save to config file')
    group.add_argument('--list-folders', action='store_true', help='List all accessible folders')
    group.add_argument('--browse-folder', metavar='FOLDER_ID', help='Browse a specific folder by ID')
    group.add_argument('--download', metavar='FILE_ID', help='Download a file by ID')
    group.add_argument('--download-path', metavar='FILE_PATH', help='Download a file by hierarchical path (e.g., Default/test/myfile.txt)')
    group.add_argument('--upload', metavar='FILE_PATH', help='Upload a file')
    group.add_argument('--stdin', action='store_true', help='Upload from standard input (requires --upload-as)')
    group.add_argument('--file-info', metavar='FILE_ID', help='Get detailed information about a file by ID')
    group.add_argument('--create-public-link', metavar='FILE_ID', help='Create a public link for a file by ID')
    group.add_argument('--delete-public-link', metavar='LINK_ID', help='Delete a public link by ID')
    group.add_argument('--delete-used-links', metavar='FILE_ID', help='Delete all used/expired public links for a file by ID')
    group.add_argument('--delete-file', metavar='FILE_ID', help='Delete a file by ID')
    group.add_argument('--delete-folder', metavar='FOLDER_ID', help='Delete a folder by ID')
    group.add_argument('--sync', metavar='LOCAL_PATH', help='Sync local directory to remote folder (rsync-like)')

    # Additional parameters
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument('--output', metavar='PATH', help='Output path for downloaded file')
    output_group.add_argument('--stdout', action='store_true', help='Write downloaded file to stdout')
    parser.add_argument('--folder', metavar='FOLDER_ID', help='Folder ID for upload')
    parser.add_argument('--folder-path', metavar='FOLDER_PATH', help='Folder path for upload (e.g., Default/test)')
    parser.add_argument('--create-folders', action='store_true', help='Create missing folders in the path automatically (use with --folder-path)')
    parser.add_argument('--upload-as', metavar='FILENAME', help='Remote filename to save uploaded file as')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing file when uploading')
    parser.add_argument('--expires-days', metavar='DAYS', type=int, help='Number of days until the public link expires')
    parser.add_argument('--max-downloads', metavar='COUNT', type=int, help='Maximum number of downloads allowed for the public link')
    parser.add_argument('--delete', action='store_true', help='Delete remote files not in local (use with --sync, like rsync --delete)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be synced without doing it (use with --sync)')

    args = parser.parse_args()

    # Load configuration from file
    load_config()

    if args.url:
        global BASE_URL
        BASE_URL = args.url

    # Handle token from command line or config
    token = args.token or TOKEN

    # Handle configure flag
    if args.configure:
        if not args.json:
            print("🔧 Configuring Container Storage CLI")
            print(f"Configuration will be saved to: {CONFIG_PATH}")

            # If token is provided via command line, use it
            if args.token:
                if save_config(args.token):
                    print(f"✅ Token saved to {CONFIG_PATH}")
                else:
                    print(f"❌ Failed to save token to {CONFIG_PATH}")
                sys.exit(0)

            # Otherwise prompt for token
            token = prompt_for_token()
            if token:
                print("✅ Configuration complete")
            else:
                print("❌ No token provided. Configuration cancelled.")
            sys.exit(0)
        else:
            # JSON output for --configure doesn't make much sense, but we'll handle it
            if args.token and save_config(args.token):
                print(json.dumps({"success": True, "message": "Token saved to config file", "config_path": CONFIG_PATH}))
            else:
                print(json.dumps({"error": "No token provided or failed to save token"}))
            sys.exit(0)

    # Create CLI instance with json_output flag and token
    cli = ContainerStorageCLI(json_output=args.json, token=token)

    # Initialize CLI (gets accessible folders)
    cli.initialize()

    # Handle command-line operations
    if args.list_folders:
        cli.list_accessible_folders()
    elif args.browse_folder:
        cli.browse_folder(args.browse_folder)
    elif args.download:
        if not cli.download_file(file_id=args.download, output_path=args.output, to_stdout=args.stdout):
            sys.exit(1)
    elif getattr(args, 'download_path', None):
        # Resolve the file path to get the file ID
        file_id = cli.resolve_file_path(args.download_path)
        if file_id is None:
            if args.json:
                cli.output_json({"error": f"File not found at path: {args.download_path}"})
            else:
                print(f"❌ File not found at path: {args.download_path}")
            sys.exit(1)

        # Download the file using the resolved ID
        if not cli.download_file(file_id=file_id, output_path=args.output, to_stdout=args.stdout):
            sys.exit(1)
    elif args.upload:
        # Determine target folder ID
        target_folder_id = None

        if getattr(args, 'folder_path', None):
            # Resolve folder path to ID
            create_missing = getattr(args, 'create_folders', False)
            target_folder_id = cli.resolve_folder_path(args.folder_path, create_missing)
            if target_folder_id is None:
                if args.json:
                    cli.output_json({"error": f"Folder not found at path: {args.folder_path}"})
                else:
                    print(f"❌ Folder not found at path: {args.folder_path}")
                sys.exit(1)
        elif args.folder:
            target_folder_id = args.folder
        elif cli.current_folder:
            target_folder_id = cli.current_folder['id']
        else:
            if args.json:
                cli.output_json({"error": "No folder specified. Use --folder FOLDER_ID or --folder-path FOLDER_PATH"})
            else:
                print("❌ No folder specified. Use --folder FOLDER_ID or --folder-path FOLDER_PATH")
            sys.exit(1)

        if not cli.upload_file(args.upload, args.overwrite, target_folder_id, getattr(args, 'upload_as', None)):
            sys.exit(1)
    elif args.stdin:
        if not args.upload_as:
            if args.json:
                cli.output_json({"error": "When using --stdin, --upload-as must be specified"})
            else:
                print("❌ When using --stdin, --upload-as must be specified")
            sys.exit(1)

        # Determine target folder ID
        target_folder_id = None

        if getattr(args, 'folder_path', None):
            # Resolve folder path to ID
            create_missing = getattr(args, 'create_folders', False)
            target_folder_id = cli.resolve_folder_path(args.folder_path, create_missing)
            if target_folder_id is None:
                if args.json:
                    cli.output_json({"error": f"Folder not found at path: {args.folder_path}"})
                else:
                    print(f"❌ Folder not found at path: {args.folder_path}")
                sys.exit(1)
        elif args.folder:
            target_folder_id = args.folder
        elif cli.current_folder:
            target_folder_id = cli.current_folder['id']
        else:
            if args.json:
                cli.output_json({"error": "No folder specified. Use --folder FOLDER_ID or --folder-path FOLDER_PATH"})
            else:
                print("❌ No folder specified. Use --folder FOLDER_ID or --folder-path FOLDER_PATH")
            sys.exit(1)

        if not cli.upload_file(None, args.overwrite, target_folder_id, args.upload_as, from_stdin=True):
            sys.exit(1)
    elif args.file_info:
        if not cli.get_file_info(file_id=args.file_info):
            sys.exit(1)
    elif args.create_public_link:
        if not cli.create_public_link(file_id=args.create_public_link, expires_days=args.expires_days, max_downloads=args.max_downloads):
            sys.exit(1)
    elif args.delete_public_link:
        if not cli.delete_public_link(args.delete_public_link):
            sys.exit(1)
    elif args.delete_used_links:
        if not cli.delete_used_public_links(args.delete_used_links):
            sys.exit(1)
    elif args.delete_file:
        # Confirm deletion unless in JSON mode
        if not args.json:
            confirm = input(f"Are you sure you want to delete file with ID {args.delete_file}? (y/N): ").lower().strip()
            if confirm != 'y':
                print("❌ File deletion cancelled.")
                sys.exit(0)

        if not cli.delete_file(args.delete_file):
            sys.exit(1)
    elif args.delete_folder:
        # Confirm deletion unless in JSON mode
        if not args.json:
            confirm = input(f"Are you sure you want to delete folder with ID {args.delete_folder}? This will delete all contents! (y/N): ").lower().strip()
            if confirm != 'y':
                print("❌ Folder deletion cancelled.")
                sys.exit(0)

        if not cli.delete_folder(args.delete_folder):
            sys.exit(1)
    elif args.sync:
        # Sync local directory to remote folder
        if not os.path.isdir(args.sync):
            if args.json:
                cli.output_json({"error": f"Local path is not a directory: {args.sync}"})
            else:
                print(f"❌ Local path is not a directory: {args.sync}")
            sys.exit(1)

        # Determine target folder ID
        target_folder_id = None

        if getattr(args, 'folder_path', None):
            # Resolve folder path to ID
            create_missing = getattr(args, 'create_folders', False)
            target_folder_id = cli.resolve_folder_path(args.folder_path, create_missing)
            if target_folder_id is None:
                if args.json:
                    cli.output_json({"error": f"Folder not found at path: {args.folder_path}"})
                else:
                    print(f"❌ Folder not found at path: {args.folder_path}")
                sys.exit(1)
        elif args.folder:
            target_folder_id = args.folder
        else:
            if args.json:
                cli.output_json({"error": "No remote folder specified. Use --folder FOLDER_ID or --folder-path FOLDER_PATH"})
            else:
                print("❌ No remote folder specified. Use --folder FOLDER_ID or --folder-path FOLDER_PATH")
            sys.exit(1)

        # Perform sync
        stats = cli.sync_directory(
            args.sync,
            target_folder_id,
            delete=args.delete,
            dry_run=args.dry_run
        )

        if args.json:
            cli.output_json(stats)

        if stats.get('errors', 0) > 0:
            sys.exit(1)
    else:
        # No operation specified, run interactive mode
        if not args.json:
            print(f"🔗 Using Storage API URL: {BASE_URL}")
            print("🔍 Container Storage CLI - Browse and manage files")
            if token:
                print("🔑 Using API token for authentication")
            else:
                print("🔒 Using container authentication")
        cli.list_accessible_folders()

        if not args.json:
            print("\nPlease select a folder to start browsing (e.g., 'select 1').")
            cli.print_help()
            cli.run()

if __name__ == '__main__':
    main()