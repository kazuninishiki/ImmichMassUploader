import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, IntVar, StringVar
import requests
import os
import threading
import concurrent.futures
from datetime import datetime, timezone
import queue
import time
import math

# --- Configuration ---
# You can change the default values here if needed
DEFAULT_IMMICH_URL = "#YOUR_IP_ADDRESS_AND_PORT"
DEFAULT_API_KEY = "#YOUR_API_KEY" 
DEFAULT_CONCURRENT_UPLOADS = 8  # Default number of concurrent uploads

# Common image and video extensions (add or remove as needed)
# Case-insensitive check will be performed
ALLOWED_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff', '.webp',
    '.heic', '.heif', '.avif',
    '.mp4', '.mov', '.avi', '.wmv', '.mkv', '.webm', '.mpg', '.mpeg',
    '.3gp'
}

# --- Core Functions ---

def format_datetime_iso(dt_object):
    """Formats a datetime object to ISO 8601 format with Z timezone."""
    # Ensure the datetime object is timezone-aware (UTC)
    if dt_object.tzinfo is None:
        # Assuming naive datetime is in local time, convert to UTC
        # For simplicity here, we'll treat naive times as UTC, which is often
        # how file system times are handled, but might need adjustment
        # depending on the source filesystem and OS.
        # A more robust approach might involve tzlocal library if needed.
        dt_object = dt_object.replace(tzinfo=timezone.utc)
    else:
        # Convert aware datetime to UTC
        dt_object = dt_object.astimezone(timezone.utc)

    # Format to ISO 8601 string ending with 'Z' for UTC
    return dt_object.strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-4] + 'Z'


def upload_file_to_immich(file_path, base_url, api_key, status_queue):
    """Uploads a single file to the Immich API."""
    filename = os.path.basename(file_path)
    api_url = f"{base_url.rstrip('/')}/api/assets"

    try:
        stats = os.stat(file_path)
        mtime_dt = datetime.fromtimestamp(stats.st_mtime, tz=timezone.utc)
        # Use mtime for both created and modified time as per example
        file_created_at_iso = format_datetime_iso(mtime_dt)
        file_modified_at_iso = file_created_at_iso

        # Generate a unique ID for the asset on the device side
        # Using path + mtime is a common strategy
        device_asset_id = f"{file_path}-{stats.st_mtime}"
        # Simple device ID
        device_id = "python-uploader-gui"

        headers = {
            'Accept': 'application/json',
            'x-api-key': api_key
        }

        data = {
            'deviceAssetId': device_asset_id,
            'deviceId': device_id,
            'fileCreatedAt': file_created_at_iso,
            'fileModifiedAt': file_modified_at_iso,
            'isFavorite': 'false',
            # Optional: Add 'isArchived', 'duration', etc. if needed/available
        }

        with open(file_path, 'rb') as f:
            files = {
                'assetData': (filename, f) # Pass filename explicitly
            }

            status_queue.put(f"Uploading: {filename}...")
            response = requests.post(api_url, headers=headers, data=data, files=files, timeout=300) # 5 min timeout

            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

            response_data = response.json()
            asset_id = response_data.get('id', 'N/A')
            is_duplicate = response_data.get('duplicate', False)

            if is_duplicate:
                status_queue.put(f"Skipped (duplicate): {filename}")
                return "skipped"
            else:
                status_queue.put(f"Uploaded: {filename} (ID: {asset_id})")
                return "success"

    except requests.exceptions.RequestException as e:
        status_queue.put(f"ERROR uploading {filename}: Network error - {e}")
        return "error"
    except IOError as e:
        status_queue.put(f"ERROR reading {filename}: {e}")
        return "error"
    except Exception as e:
        status_queue.put(f"ERROR processing {filename}: {e}")
        return "error"

# --- GUI Class ---

class ImmichUploaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Immich Folder Uploader")
        self.root.geometry("600x550")  # Increased height for progress bar

        self.status_queue = queue.Queue()
        self.upload_thread = None
        
        # Initialize tracking variables
        self.processed_files = 0
        self.total_files = 0
        self.success_count = 0
        self.skipped_count = 0
        self.error_count = 0

        # Style
        style = ttk.Style(self.root)
        style.theme_use('clam') # Or 'alt', 'default', 'classic'

        # --- Configuration Frame ---
        config_frame = ttk.LabelFrame(self.root, text="Configuration", padding="10")
        config_frame.pack(padx=10, pady=10, fill=tk.X)

        ttk.Label(config_frame, text="Immich URL:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.url_entry = ttk.Entry(config_frame, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        self.url_entry.insert(0, DEFAULT_IMMICH_URL)

        ttk.Label(config_frame, text="API Key:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.api_key_entry = ttk.Entry(config_frame, width=50, show="*")
        self.api_key_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        self.api_key_entry.insert(0, DEFAULT_API_KEY)
        
        # Thread count configuration
        ttk.Label(config_frame, text="Concurrent Uploads:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.thread_count = IntVar(value=DEFAULT_CONCURRENT_UPLOADS)  # Default to 8 threads
        thread_spinner = ttk.Spinbox(config_frame, from_=1, to=32, textvariable=self.thread_count, width=5)
        thread_spinner.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        config_frame.columnconfigure(1, weight=1) # Make entry expand

        # --- Folder Selection Frame ---
        folder_frame = ttk.LabelFrame(self.root, text="Folder Selection", padding="10")
        folder_frame.pack(padx=10, pady=5, fill=tk.X)

        self.folder_label = ttk.Label(folder_frame, text="No folder selected", wraplength=450)
        self.folder_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        self.browse_button = ttk.Button(folder_frame, text="Browse...", command=self.select_folder)
        self.browse_button.grid(row=0, column=1, padx=5, pady=5, sticky=tk.E)

        folder_frame.columnconfigure(0, weight=1) # Make label expand

        self.selected_folder = None
        
        # --- Progress Frame ---
        progress_frame = ttk.LabelFrame(self.root, text="Upload Progress", padding="10")
        progress_frame.pack(padx=10, pady=5, fill=tk.X)
        
        self.progress_var = IntVar()
        self.progress_label = StringVar(value="0/0 files processed (0%)")
        
        ttk.Label(progress_frame, textvariable=self.progress_label).pack(fill=tk.X, pady=2)
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            variable=self.progress_var, 
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, pady=2)

        # --- Control Frame ---
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(padx=10, pady=5, fill=tk.X)

        self.upload_button = ttk.Button(control_frame, text="Start Upload", command=self.start_upload)
        self.upload_button.pack(side=tk.LEFT, padx=5)
        self.upload_button.config(state=tk.DISABLED) # Disabled until folder is selected

        # --- Status Frame ---
        status_frame = ttk.LabelFrame(self.root, text="Status Log", padding="10")
        status_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.status_text = scrolledtext.ScrolledText(status_frame, wrap=tk.WORD, height=15, state=tk.DISABLED)
        self.status_text.pack(fill=tk.BOTH, expand=True)

        # Start checking the queue
        self.check_queue()

    def select_folder(self):
        """Opens a dialog to select a folder."""
        folder = filedialog.askdirectory(title="Select Folder Containing Photos/Videos")
        if folder:
            self.selected_folder = folder
            self.folder_label.config(text=folder)
            self.upload_button.config(state=tk.NORMAL) # Enable upload button
            self.log_status(f"Selected folder: {folder}")
        else:
            self.folder_label.config(text="No folder selected")
            self.upload_button.config(state=tk.DISABLED) # Disable if no folder

    def start_upload(self):
        """Starts the upload process using a thread pool."""
        if not self.selected_folder:
            self.log_status("ERROR: Please select a folder first.")
            return
        if self.upload_thread and self.upload_thread.is_alive():
            self.log_status("INFO: Upload already in progress.")
            return

        url = self.url_entry.get().strip()
        api_key = self.api_key_entry.get().strip()

        if not url or not api_key:
            self.log_status("ERROR: Immich URL and API Key cannot be empty.")
            return

        # Clear status log for new run
        self.clear_status()
        self.log_status("Starting upload...")
        self.upload_button.config(state=tk.DISABLED)
        self.browse_button.config(state=tk.DISABLED)

        # Reset progress
        self.progress_var.set(0)
        self.progress_label.set("0/0 files processed (0%)")
        
        # Reset counters
        self.processed_files = 0
        self.success_count = 0
        self.skipped_count = 0
        self.error_count = 0

        # Create and start the worker thread
        self.upload_thread = threading.Thread(
            target=self.discover_and_upload_files,
            args=(self.selected_folder, url, api_key, self.thread_count.get()),
            daemon=True # Allows main program to exit even if thread is running
        )
        self.upload_thread.start()

    def discover_and_upload_files(self, folder_path, base_url, api_key, thread_count):
        """Discovers all uploadable files and then processes them with a thread pool."""
        self.log_status(f"Scanning folder for media files...")
        
        # First, discover all eligible files
        eligible_files = []
        total_files_scanned = 0
        
        for root, _, files in os.walk(folder_path):
            for filename in files:
                total_files_scanned += 1
                file_path = os.path.join(root, filename)
                _, file_extension = os.path.splitext(filename)

                if file_extension.lower() in ALLOWED_EXTENSIONS:
                    eligible_files.append(file_path)
        
        self.log_status(f"Found {len(eligible_files)} eligible files out of {total_files_scanned} total files.")
        self.total_files = len(eligible_files)
        
        if self.total_files == 0:
            self.status_queue.put("No eligible files found for upload.")
            self.status_queue.put(None)  # Signal completion
            return
            
        # Update progress label initially
        self.update_progress_label()
        
        # Use a thread pool to upload files concurrently
        self.log_status(f"Starting uploads with {thread_count} concurrent workers...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
            # Submit all upload tasks
            future_to_file = {
                executor.submit(upload_file_to_immich, file_path, base_url, api_key, self.status_queue): file_path
                for file_path in eligible_files
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    self.processed_files += 1
                    
                    if result == "success":
                        self.success_count += 1
                    elif result == "skipped":
                        self.skipped_count += 1
                    else:
                        self.error_count += 1
                        
                    # Update progress
                    self.update_progress()
                    
                except Exception as e:
                    self.status_queue.put(f"ERROR processing {os.path.basename(file_path)}: {e}")
                    self.error_count += 1
                    self.processed_files += 1
                    self.update_progress()

        # Upload complete
        self.status_queue.put("\n----- Upload Complete -----")
        self.status_queue.put(f"Total files scanned: {total_files_scanned}")
        self.status_queue.put(f"Eligible files: {self.total_files}")
        self.status_queue.put(f"Successfully uploaded: {self.success_count}")
        self.status_queue.put(f"Skipped (duplicates): {self.skipped_count}")
        self.status_queue.put(f"Errors: {self.error_count}")
        self.status_queue.put("----- Done -----")
        self.status_queue.put(None)  # Signal completion

    def update_progress(self):
        """Updates the progress bar and label based on processed files."""
        # Calculate percentage
        if self.total_files > 0:
            percentage = math.floor((self.processed_files / self.total_files) * 100)
            self.progress_var.set(percentage)
            
            # Update label with count and percentage
            self.update_progress_label()
    
    def update_progress_label(self):
        """Updates the progress label with current counts."""
        if self.total_files > 0:
            percentage = math.floor((self.processed_files / self.total_files) * 100)
            self.progress_label.set(
                f"{self.processed_files}/{self.total_files} files processed ({percentage}%)"
            )

    def check_queue(self):
        """Checks the status queue and updates the UI."""
        try:
            while True:
                message = self.status_queue.get_nowait()
                if message is None: # Sentinel value means thread finished
                    self.upload_finished()
                    break # Exit loop for this check cycle
                else:
                    self.log_status(message)
        except queue.Empty:
            pass # No messages currently in queue

        # Schedule the next check
        self.root.after(100, self.check_queue) # Check again in 100ms

    def upload_finished(self):
        """Called when the worker thread signals completion."""
        self.log_status("INFO: Upload process finished.")
        self.upload_button.config(state=tk.NORMAL if self.selected_folder else tk.DISABLED)
        self.browse_button.config(state=tk.NORMAL)
        self.upload_thread = None # Reset thread variable

    def log_status(self, message):
        """Appends a message to the status text area."""
        self.status_text.config(state=tk.NORMAL) # Enable writing
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END) # Scroll to the bottom
        self.status_text.config(state=tk.DISABLED) # Disable writing

    def clear_status(self):
        """Clears the status text area."""
        self.status_text.config(state=tk.NORMAL) # Enable writing
        self.status_text.delete('1.0', tk.END)
        self.status_text.config(state=tk.DISABLED) # Disable writing

# --- Main Execution ---
if __name__ == "__main__":
    main_root = tk.Tk()
    app = ImmichUploaderApp(main_root)
    main_root.mainloop()