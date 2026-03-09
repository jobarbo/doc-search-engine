#!/usr/bin/env python3
import os
import json
import PyPDF2

PDF_DIRS = {
    "main": "public/pdfs/main",
    "other": "public/pdfs/other"
}

def build_index():
    index_data = []

    for folder_key, folder_path in PDF_DIRS.items():
        if not os.path.exists(folder_path):
            print(f"Directory not found: {folder_path}")
            continue

        pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
        
        for filename in pdf_files:
            file_path = os.path.join(folder_path, filename)
            print(f"Indexing: {filename} from {folder_key}")
            
            doc_data = {
                "filename": filename,
                "folder": folder_key,
                "path": f"/pdfs/{folder_key}/{filename}",
                "pages": []
            }
            
            try:
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    num_pages = len(reader.pages)
                    
                    for i in range(num_pages):
                        try:
                            page = reader.pages[i]
                            text = page.extract_text()
                            if text and text.strip():
                                doc_data["pages"].append({
                                    "page_number": i + 1,
                                    "text": text.strip()
                                })
                        except Exception as page_e:
                            print(f"  Error reading page {i+1} of {filename}: {str(page_e)}")
            except Exception as e:
                print(f"Error opening {filename}: {str(e)}")
                
            index_data.append(doc_data)

    output_path = "public/search_index.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False)
        
    print(f"\nSuccessfully built static index with {len(index_data)} PDFs at {output_path}")

if __name__ == "__main__":
    build_index()
