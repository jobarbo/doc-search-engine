#!/usr/bin/env python3
"""
PDF Search Web App - A Flask web application for searching PDF content
"""

from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import os
import pdf_indexer
import datetime
import traceback
import sys
import flask
import whoosh

app = Flask(__name__)
app.secret_key = 'pdf_search_secret_key'  # Required for flash messages

@app.context_processor
def inject_now():
    """Add the current date to all templates"""
    return {'now': datetime.datetime.now()}

@app.context_processor
def inject_folders():
    """Add the available PDF folders to all templates"""
    return {'folders': pdf_indexer.get_available_folders()}

@app.route('/')
def index():
    """Render the home page with search box"""
    # Get the selected folder from the query parameter, default to "main"
    folder = request.args.get('folder', 'main')

    # Check if the index exists, if not, build it
    index_dir = f"pdf_index_{folder}"
    if not os.path.exists(index_dir):
        try:
            pdf_indexer.build_index(folder)
        except Exception as e:
            error_message = f"Error building index for {folder}: {str(e)}"
            return render_template('index.html', error=error_message, selected_folder=folder)

    # Count the PDFs in the directory
    pdf_count = 0
    try:
        pdf_count = pdf_indexer.get_pdf_count(folder)
    except Exception as e:
        app.logger.error(f"Error counting PDFs in {folder}: {str(e)}")

    return render_template('index.html', pdf_count=pdf_count, selected_folder=folder)

@app.route('/search')
def search():
    """Handle search requests"""
    query = request.args.get('query', '')
    folder = request.args.get('folder', 'main')
    exact_match = request.args.get('exact_match') == '1'

    if not query:
        return redirect(url_for('index', folder=folder))

    app.logger.info(f"Search request for: '{query}' in folder: {folder}, exact match: {exact_match}")

    try:
        # Search the index
        results = pdf_indexer.search_index(query, folder, exact_match=exact_match)

        app.logger.info(f"Found {len(results)} results for '{query}' in folder: {folder}")

        if not results:
            # Log some info about the PDFs and index
            pdf_dir = pdf_indexer.PDF_DIRS.get(folder, pdf_indexer.DEFAULT_PDF_DIR)
            if os.path.exists(pdf_dir):
                pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
                app.logger.info(f"PDF directory {pdf_dir} contains {len(pdf_files)} files: {pdf_files}")

            index_dir = f"pdf_index_{folder}"
            if os.path.exists(index_dir):
                app.logger.info(f"Index exists for {folder}")
            else:
                app.logger.error(f"Index does not exist for {folder}")

        return render_template(
            'search_results.html',
            query=query,
            results=results,
            result_count=len(results),
            selected_folder=folder,
            exact_match=exact_match
        )
    except Exception as e:
        error_trace = traceback.format_exc()
        app.logger.error(f"Search error: {str(e)}\n{error_trace}")
        return render_template('search_results.html', query=query, error=str(e), results=[], result_count=0, selected_folder=folder, exact_match=exact_match)

@app.route('/view/<filename>')
def view_pdf(filename):
    """View/download a PDF file with optional page navigation"""
    try:
        folder = request.args.get('folder', 'main')
        page = request.args.get('page', None)

        # If a page number is specified, render HTML with embedded PDF at that page
        if page:
            app.logger.info(f"Viewing PDF: {filename} from folder: {folder}, opening at page: {page}")
            return render_template('view_pdf.html', filename=filename, folder=folder, page=page)
        else:
            # Direct file serving for backward compatibility
            pdf_dir = pdf_indexer.PDF_DIRS.get(folder, pdf_indexer.DEFAULT_PDF_DIR)
            pdf_path = os.path.join(pdf_dir, filename)
            app.logger.info(f"Serving PDF: {pdf_path} from folder: {folder}")
            return send_file(pdf_path, as_attachment=False)
    except Exception as e:
        app.logger.error(f"Error opening file: {str(e)}")
        return f"Error opening file: {str(e)}"

@app.route('/pdf/<folder>/<filename>')
def serve_pdf(folder, filename):
    """Serve the actual PDF file"""
    try:
        pdf_dir = pdf_indexer.PDF_DIRS.get(folder, pdf_indexer.DEFAULT_PDF_DIR)
        pdf_path = os.path.join(pdf_dir, filename)
        return send_file(pdf_path, as_attachment=False, mimetype='application/pdf')
    except Exception as e:
        app.logger.error(f"Error serving PDF: {str(e)}")
        return f"Error serving PDF: {str(e)}"

@app.route('/rebuild-index')
def rebuild_index():
    """Rebuild the search index"""
    try:
        folder = request.args.get('folder', 'main')
        app.logger.info(f"Rebuilding index for folder: {folder}...")
        count = pdf_indexer.build_index(folder)
        app.logger.info(f"Indexed {count} PDF files from folder: {folder}")
        return render_template('index.html', success=f"Successfully indexed {count} PDF files from {folder}", pdf_count=count, selected_folder=folder)
    except Exception as e:
        folder = request.args.get('folder', 'main')
        error_trace = traceback.format_exc()
        app.logger.error(f"Index rebuild error for {folder}: {str(e)}\n{error_trace}")
        return render_template('index.html', error=f"Error rebuilding index for {folder}: {str(e)}", selected_folder=folder)

@app.route('/debug')
def debug_info():
    """Display debug information"""
    folder = request.args.get('folder', 'main')
    pdf_dir = pdf_indexer.PDF_DIRS.get(folder, pdf_indexer.DEFAULT_PDF_DIR)
    index_dir = f"pdf_index_{folder}"

    debug_data = {
        "pdf_directory": pdf_dir,
        "pdf_directory_exists": os.path.exists(pdf_dir),
        "pdf_files": [],
        "index_directory": index_dir,
        "index_exists": os.path.exists(index_dir),
        "python_version": sys.version,
        "flask_version": flask.__version__,
        "whoosh_version": whoosh.__version__ if 'whoosh' in sys.modules else "Unknown",
        "available_folders": pdf_indexer.get_available_folders(),
        "parent_directory": pdf_indexer.PDF_PARENT_DIR,
        "parent_directory_exists": os.path.exists(pdf_indexer.PDF_PARENT_DIR)
    }

    # Get PDF files
    if debug_data["pdf_directory_exists"]:
        debug_data["pdf_files"] = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]

    return render_template('debug.html', debug=debug_data, selected_folder=folder)

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.mkdir('templates')

    # Ensure parent PDF directory exists
    if not os.path.exists(pdf_indexer.PDF_PARENT_DIR):
        os.makedirs(pdf_indexer.PDF_PARENT_DIR)
        print(f"Created parent PDF directory: {pdf_indexer.PDF_PARENT_DIR}")

    # Ensure all PDF directories exist
    for folder_key, folder_path in pdf_indexer.PDF_DIRS.items():
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Created PDF directory: {folder_path}")

    # Run the Flask app with a different port and bind to all interfaces
    port = 8080  # Using port 8080 instead of 5000
    print(f"Starting Flask app at http://127.0.0.1:{port}/")
    app.run(debug=True, host='0.0.0.0', port=port)