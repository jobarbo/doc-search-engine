# PDF Search Website

Simple web application for searching and extracting text from PDF files.

## Project Structure

- `pdfs/` - Directory containing all PDF files
  - `pdfs/main/` - Main directory for PDF files
  - `pdfs/other/` - Secondary directory for PDF files
- `pdf_index_main/` - Directory where the search index for main folder is stored
- `pdf_index_other/` - Directory where the search index for other folder is stored
- `static/` - Static assets (CSS, JS)
- `templates/` - HTML templates

## Prerequisites

You need Python 3.6+ and the following libraries:

- PyPDF2
- pdfminer.six
- Flask
- Whoosh
- pytesseract
- pdf2image
- Pillow

Additionally, you need to install Tesseract OCR and Poppler:

### On macOS:

```bash
brew install tesseract
brew install poppler
```

### On Ubuntu/Debian:

```bash
sudo apt-get install tesseract-ocr
sudo apt-get install poppler-utils
```

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Available Scripts

### pdf_indexer.py

This script extracts text from PDFs and builds a searchable index:

```bash
python3 pdf_indexer.py
```

### app.py

The Flask web application that provides the search interface:

```bash
python3 app.py
```

After running the app, access the website at: http://127.0.0.1:8080

## Features

- **Search**: Search for any term within your PDF files
- **Results**: View highlighted snippets showing where the term appears
- **View PDFs**: Open PDFs directly from the search results
- **Rebuild Index**: Easily rebuild the search index if you add new PDFs
- **Multiple Folders**: Search in different PDF folders
- **OCR Support**: Extract text from scanned PDFs using Optical Character Recognition
- **Debug Information**: View system and application information for troubleshooting

## Notes

- PDFs can be placed in either the `pdfs/main/` or `pdfs/other/` directory
- The application now supports OCR for scanned PDFs or PDFs without extractable text
- If you add new PDF files, use the "Rebuild Index" button in the web interface
- OCR processing may take longer for large PDF files or files with many pages
