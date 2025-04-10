# Multi-Threaded Immich Uploader

A Python GUI application for efficiently uploading media files to an Immich server with concurrent processing support.

![Immich Uploader Screenshot](https://github.com/yourusername/immich-uploader/raw/main/screenshots/uploader.png)

## Features

- **Multi-threaded uploads**: Process multiple files simultaneously for faster transfers
- **Configurable concurrency**: Set 1-32 concurrent uploads based on your network and server capabilities
- **Progress tracking**: Real-time progress bar and status updates
- **Recursive folder scanning**: Automatically finds all eligible media files in subfolders
- **Smart file detection**: Only uploads compatible image and video formats
- **Duplicate detection**: Automatically skips files already present on the server
- **Error handling**: Robust error handling with detailed logs

## Supported File Types

### Images
- JPEG/JPG
- PNG
- GIF
- BMP
- TIFF/TIF
- WebP
- HEIC/HEIF
- AVIF

### Videos
- MP4
- MOV
- AVI
- WMV
- MKV
- WebM
- MPG/MPEG
- 3GP

## Requirements

- Python 3.6+
- Tkinter (usually included with Python)
- Requests library

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/immich-uploader.git
   cd immich-uploader
   ```

2. Install the required dependencies:
   ```bash
   pip install requests
   ```

3. Run the application:
   ```bash
   python immich_uploader.py
   ```

## Configuration

The application allows configuration of:

- **Immich Server URL**: The base URL of your Immich server (e.g., `http://192.168.1.100:2283`)
- **API Key**: Your personal Immich API key (found in Immich settings)
- **Concurrent Uploads**: Number of files to upload simultaneously (default: 8)

### Obtaining Your API Key

1. Log in to your Immich web interface
2. Go to User Settings
3. Navigate to Security & API Keys
4. Create a new API key for the uploader application
5. Copy the API key to use in the uploader

## Usage

1. Enter your Immich server URL and API key
2. Set the desired number of concurrent uploads (higher numbers may speed up uploads but increase server load)
3. Click "Browse" to select the folder containing your photos and videos
4. Click "Start Upload" to begin the process
5. Monitor progress in the status log and progress bar
6. Wait for the "Upload process finished" message

## How It Works

The uploader:

1. Recursively scans the selected folder and all subfolders for media files
2. Filters for supported file formats
3. Creates a thread pool for concurrent uploads
4. Uploads files using the Immich API
5. Tracks progress and handles errors
6. Provides a summary when complete

## Troubleshooting

### Common Issues

- **API Key Errors**: Make sure you've entered a valid API key from your Immich server
- **Connection Errors**: Check that your Immich server URL is correct and accessible
- **Slow Uploads**: Try reducing the concurrent uploads value if your network connection is unstable
- **Timeouts**: Large files might time out - the default timeout is 5 minutes per file

### Error Logs

The status log at the bottom of the application provides detailed information about any errors that occur during the upload process.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Immich](https://github.com/immich-app/immich) - The excellent self-hosted photo and video backup solution
- [Requests](https://docs.python-requests.org/en/latest/) - The elegant HTTP library for Python
- [Tkinter](https://docs.python.org/3/library/tkinter.html) - Standard Python interface to Tk GUI toolkit

## Disclaimer

This is an unofficial tool and is not affiliated with or endorsed by the Immich project.
