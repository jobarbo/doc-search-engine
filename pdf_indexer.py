#!/usr/bin/env python3
"""
PDF Indexer - Extract text from PDFs and create a searchable index
"""

import os
import sys
import PyPDF2
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, STORED
from whoosh.qparser import QueryParser, MultifieldParser, OrGroup
import shutil
from whoosh.analysis import StemmingAnalyzer
import tempfile
import pytesseract
from pdf2image import convert_from_path

# Define the PDF directories
PDF_DIRS = {
    "main": "pdfs/main",
    "other": "pdfs/other"
}

# Parent PDF directory
PDF_PARENT_DIR = "pdfs"

# Default PDF directory
DEFAULT_PDF_DIR = "pdfs/main"

def extract_text_from_pdf(file_path):
    """Extract text from all pages of a PDF file, using OCR if needed"""
    text = ""
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = len(reader.pages)

            # Extract text from all pages
            for i in range(num_pages):
                page = reader.pages[i]
                page_text = page.extract_text()
                if page_text:
                    text += f"Page {i+1}:\n{page_text}\n\n"

        # If no text was extracted, try OCR
        if not text.strip():
            print(f"No text extracted from {file_path}, trying OCR...")
            text = extract_text_with_ocr(file_path)

        return text
    except Exception as e:
        print(f"Error extracting text from {file_path}: {str(e)}")
        return ""

def extract_text_with_ocr(pdf_path):
    """Extract text from PDF using OCR"""
    try:
        text = ""
        # Create a temporary directory for the images
        with tempfile.TemporaryDirectory() as temp_dir:
            # Convert PDF to images
            print(f"Converting PDF to images: {pdf_path}")
            images = convert_from_path(pdf_path)

            # Process each page
            for i, image in enumerate(images):
                # Save the image temporarily
                image_path = os.path.join(temp_dir, f'page_{i+1}.png')
                image.save(image_path, 'PNG')

                # Extract text using OCR
                print(f"Performing OCR on page {i+1}/{len(images)}")
                page_text = pytesseract.image_to_string(image_path)
                if page_text:
                    text += f"Page {i+1}:\n{page_text}\n\n"

        return text
    except Exception as e:
        print(f"OCR error for {pdf_path}: {str(e)}")
        return ""

def build_index(pdf_dir_key="main"):
    """Build or rebuild the search index from all PDF files in the specified directory"""
    # Get the actual directory path from the key
    pdf_dir = PDF_DIRS.get(pdf_dir_key, DEFAULT_PDF_DIR)

    # Define the schema for our index with better text analysis

    # Create analyzer that will work well for French and English content
    analyzer = StemmingAnalyzer(minsize=2)

    schema = Schema(
        filename=ID(stored=True),
        path=ID(stored=True),
        content=TEXT(stored=True, analyzer=analyzer),
        source_folder=ID(stored=True)  # Store which folder this PDF came from
    )

    # Create index directory if it doesn't exist
    # Use a folder-specific index
    index_dir = f"pdf_index_{pdf_dir_key}"
    if os.path.exists(index_dir):
        # Remove existing index
        shutil.rmtree(index_dir)
    os.mkdir(index_dir)

    # Create the index
    index = create_in(index_dir, schema)
    writer = index.writer()

    # Find all PDF files in the PDFs directory
    if not os.path.exists(pdf_dir):
        print(f"PDF directory '{pdf_dir}' does not exist.")
        os.makedirs(pdf_dir)
        return 0

    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]

    # Process each PDF
    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_dir, pdf_file)
        print(f"Indexing: {pdf_file} from {pdf_dir}")
        text = extract_text_from_pdf(pdf_path)

        # Add document to index
        writer.add_document(
            filename=pdf_file,
            path=os.path.abspath(pdf_path),
            content=text,
            source_folder=pdf_dir_key
        )

    # Commit changes and close the writer
    writer.commit()
    print(f"Indexed {len(pdf_files)} PDF files from {pdf_dir}.")
    return len(pdf_files)

def get_pdf_count(pdf_dir_key="main"):
    """Get the number of PDF files in the specified directory"""
    pdf_dir = PDF_DIRS.get(pdf_dir_key, DEFAULT_PDF_DIR)
    if not os.path.exists(pdf_dir):
        return 0
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
    return len(pdf_files)

def get_available_folders():
    """Return a list of available PDF folders"""
    return [(key, path) for key, path in PDF_DIRS.items()]

def search_index(query_text, pdf_dir_key="main", exact_match=False):
    """Search the index for the given query in the specified folder"""
    try:
        # Open the index for the specified folder
        index_dir = f"pdf_index_{pdf_dir_key}"
        if not os.path.exists(index_dir):
            print(f"Index doesn't exist for {pdf_dir_key}. Please build the index first.")
            return []

        index = open_dir(index_dir)

        # Process the query to make it more lenient
        # Replace any special characters with spaces
        import re
        cleaned_query = re.sub(r'[^\w\s]', ' ', query_text)

        # Store original terms for precise highlighting
        original_terms = cleaned_query.split()
        if not original_terms:
            return []

        # Debug: Print terms after cleaning
        print(f"Terms after cleaning: {original_terms}")

        # Create a comprehensive search query that combines:
        # 1. Exact term matching
        # 2. Wildcard matching for partial words
        # 3. Prefix matching (beginning of words)
        # 4. Exact phrase matching (if multiple terms)
        all_query_parts = []

        if exact_match:
            # For exact matching, use phrase query with proper escaping
            # Escape the query to avoid any special character issues
            escaped_query = query_text.replace('"', '\\"')
            search_query = f'"{escaped_query}"'
            print(f"Exact match search query: {search_query}")
        else:
            # For regular search, we rely primarily on the analyzer's stemming
            # to match terms flexibly, rather than wildcards which bypass stemming

            # Add the exact phrase if multiple terms
            if len(original_terms) > 1:
                all_query_parts.append(f'"{query_text}"')  # Add exact phrase in quotes

            # Add individual terms - let the analyzer handle stemming and variants
            for term in original_terms:
                # Add the term (will be stemmed by the analyzer)
                all_query_parts.append(term)

            # Join all parts with OR - the stemming analyzer will handle variations
            search_query = " OR ".join(all_query_parts)
            print(f"Regular search query: {search_query}")

        # Search the index
        with index.searcher() as searcher:
            if exact_match:
                # For exact match, use a strict phrase parser without fuzzy matching
                query_parser = QueryParser("content", index.schema)
                query = query_parser.parse(search_query)
            else:
                # For regular search, use lenient OR group matching
                query_parser = QueryParser("content", index.schema, group=OrGroup.factory(0.9))
                query = query_parser.parse(search_query)

            print(f"Searching for: {search_query} in folder: {pdf_dir_key}")
            results = searcher.search(query, limit=None)
            print(f"Found {len(results)} results")

            # Debug: Print raw results
            for i, hit in enumerate(results):
                print(f"Result {i+1}: {hit['filename']}")

            # Format search results
            search_results = []
            print(f"DEBUG: About to process {len(results)} results with exact_match={exact_match}")
            sys.stdout.flush()
            for result in results:
                # Get highlighted snippets with simpler parameters
                print(f"DEBUG: Processing result: {result['filename']}")
                sys.stdout.flush()
                try:
                    # First try with just the field name to get the basic highlights
                    highlights = result.highlights("content")

                    # Now apply custom highlighting to highlight only the exact search terms
                    if highlights:
                        # Get the content for more accurate highlighting
                        content = result.get("content", "")

                        # Create a custom highlighted version
                        custom_highlights = highlights

                        # Function to create precise highlighting
                        def highlight_exact_terms(text, terms, is_exact_match):
                            # For case insensitive matching
                            terms_lower = [t.lower() for t in terms]

                            # Also check for the complete phrase if multiple terms
                            original_query = query_text.lower()

                            # Find the context around matches (300 chars)
                            contexts = []
                            lines = text.split('\n')

                            for line in lines:
                                line_lower = line.lower()

                                # For exact match mode, ONLY match the complete phrase
                                if is_exact_match:
                                    if original_query in line_lower:
                                        # Extract context around the phrase
                                        start_idx = max(0, line_lower.find(original_query) - 50)
                                        end_idx = min(len(line), line_lower.find(original_query) + len(original_query) + 50)
                                        context = line[start_idx:end_idx]

                                        # Find the exact phrase in the context with proper case preservation
                                        phrase_start = line_lower[start_idx:end_idx].find(original_query)
                                        if phrase_start >= 0:
                                            phrase_end = phrase_start + len(original_query)
                                            exact_phrase = context[phrase_start:phrase_end]
                                            highlighted = f'<b class="match term0">{exact_phrase}</b>'
                                            context = context[:phrase_start] + highlighted + context[phrase_end:]
                                            contexts.append(context)
                                else:
                                    # For regular search, check for phrase first, then individual terms
                                    # First check for exact phrase match if multiple terms
                                    if len(terms) > 1 and original_query in line_lower:
                                        # Extract context around the phrase
                                        start_idx = max(0, line_lower.find(original_query) - 50)
                                        end_idx = min(len(line), line_lower.find(original_query) + len(original_query) + 50)
                                        context = line[start_idx:end_idx]

                                        # Find the exact phrase in the context with proper case preservation
                                        phrase_start = line_lower[start_idx:end_idx].find(original_query)
                                        if phrase_start >= 0:
                                            phrase_end = phrase_start + len(original_query)
                                            exact_phrase = context[phrase_start:phrase_end]
                                            highlighted = f'<b class="match term0">{exact_phrase}</b>'
                                            context = context[:phrase_start] + highlighted + context[phrase_end:]
                                            contexts.append(context)
                                            continue

                                    # Fall back to individual term matching for regular search
                                    for term in terms_lower:
                                        if term in line_lower:
                                            # Extract context around the term
                                            start_idx = max(0, line_lower.find(term) - 50)
                                            end_idx = min(len(line), line_lower.find(term) + len(term) + 50)
                                            context = line[start_idx:end_idx]

                                            # Highlight just the term with proper case preservation
                                            for i, char in enumerate(context):
                                                if i+len(term) <= len(context) and context[i:i+len(term)].lower() == term:
                                                    exact_term = context[i:i+len(term)]
                                                    highlighted = f'<b class="match term0">{exact_term}</b>'
                                                    context = context[:i] + highlighted + context[i+len(term):]
                                                    break

                                            contexts.append(context)
                                            break  # Only add one context per line

                            # Join contexts with separators
                            if contexts:
                                return "\n[...]\n".join(contexts)
                            return ""

                        # Try to apply more precise highlighting
                        precise_highlights = highlight_exact_terms(content, original_terms, exact_match)
                        if precise_highlights:
                            highlights = precise_highlights

                    print(f"Simple highlights for {result['filename']}: {highlights[:100] if highlights else 'None'}")
                except Exception as highlight_error:
                    print(f"Error getting highlights: {str(highlight_error)}")
                    # If highlighting fails, just use a portion of the content as a fallback
                    content = result.get("content", "")
                    highlights = content[:300] + "..." if content else "No preview available"

                # Add page indicator to result if possible
                print(f"DEBUG: Starting page detection for {result['filename']}")
                sys.stdout.flush()
                page_match = ""
                first_page = None

                try:
                    # Get the full content to search for page numbers
                    content = result.get("content", "")
                    print(f"DEBUG: Got content, length: {len(content)}")
                    sys.stdout.flush()

                    # Find which pages contain the search terms
                    import re
                    if exact_match:
                        # For exact match, find the phrase
                        # Normalize apostrophes and quotes to handle different character encodings
                        def normalize_text(text):
                            # Replace various apostrophes and quotes with standard versions
                            text = text.replace("'", "'").replace("'", "'")  # Curly apostrophes
                            text = text.replace(""", '"').replace(""", '"')  # Curly quotes
                            text = text.replace("«", '"').replace("»", '"')  # French quotes
                            return text

                        query_lower = normalize_text(query_text.lower())
                        content_lower = normalize_text(content.lower())
                        print(f"DEBUG: Looking for exact match of '{query_lower[:50]}...' in content")
                        if query_lower in content_lower:
                            # Find the position of the match
                            match_pos = content_lower.find(query_lower)
                            print(f"DEBUG: Found match at position {match_pos}")
                            # Find the last "Page X:" marker before this position
                            content_before_match = content[:match_pos]
                            page_markers = re.findall(r'Page (\d+):', content_before_match)
                            print(f"DEBUG: Page markers found before match: {page_markers}")
                            if page_markers:
                                first_page = int(page_markers[-1])  # Last page marker before match
                                page_match = f" - Found on page {first_page}"
                                print(f"DEBUG: Set first_page to {first_page}")
                            else:
                                print(f"DEBUG: No page markers found before match position")
                        else:
                            print(f"DEBUG: Query not found in content")
                    else:
                        # For regular search, find any page with matching terms
                        # Look through content to find pages with matches
                        page_markers_all = re.findall(r'Page (\d+):', content)
                        print(f"DEBUG: Regular search - found {len(page_markers_all)} page markers total")
                        if page_markers_all and highlights:
                            # Use the first page number as a best guess
                            first_page = int(page_markers_all[0])
                            page_match = f" - Found on page {first_page}"
                            print(f"DEBUG: Set first_page to {first_page}")

                except Exception as page_error:
                    print(f"DEBUG: Error in page detection: {str(page_error)}")
                    import traceback
                    traceback.print_exc()
                    sys.stdout.flush()

                # Get the source folder
                source_folder = result.get("source_folder", pdf_dir_key)

                search_results.append({
                    "filename": result["filename"],
                    "path": result["path"],
                    "page_match": page_match,
                    "page_number": first_page,  # Add page number for direct linking
                    "highlights": highlights if highlights else "Match found, but no context to display",
                    "source_folder": source_folder
                })

            print(f"Formatted {len(search_results)} results")
            return search_results
    except Exception as e:
        import traceback
        print(f"Error searching index: {str(e)}")
        print(traceback.format_exc())
        return []

if __name__ == "__main__":
    # If run directly, build the index for both folders
    # Ensure parent directory exists
    if not os.path.exists(PDF_PARENT_DIR):
        os.makedirs(PDF_PARENT_DIR)
        print(f"Created parent PDF directory: {PDF_PARENT_DIR}")

    # Ensure all subdirectories exist
    for folder_key, folder_path in PDF_DIRS.items():
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Created PDF directory: {folder_path}")

    print("Building index for main folder...")
    build_index("main")
    print("\nBuilding index for other folder...")
    build_index("other")