import PyPDF2
import os

# Function to extract specific pages from PDF
def extract_pages(input_pdf, output_pdf, start_page, end_page):
    """
    Extract pages from a PDF and save as new PDF
    """
    try:
        # Open the source PDF
        with open(input_pdf, 'rb') as source_file:
            pdf_reader = PyPDF2.PdfReader(source_file)
            pdf_writer = PyPDF2.PdfWriter()
            
            # Pages are 0-indexed in PyPDF2, so subtract 1
            for page_num in range(start_page - 1, end_page):
                if page_num < len(pdf_reader.pages):
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                    print(f"✓ Added page {page_num + 1}")
                else:
                    print(f"✗ Page {page_num + 1} does not exist")
            
            # Save the extracted pages
            with open(output_pdf, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            print(f"\n Success! Extracted {end_page - start_page + 1} pages to: {output_pdf}")
            return True
            
    except Exception as e:
        print(f" Error: {e}")
        return False

# ============================================
# CONFIGURE THESE PATHS
# ============================================

# CHANGE THIS: Path to your 250-page PDF file
input_pdf_path = r"D:\UNIVERSITY\6th Semester\LLM\LLMS-Project\data.pdf"  

# Output file name
output_pdf_path = r"D:\UNIVERSITY\6th Semester\LLM\LLMS-Project\candidate_1.pdf"


start_page = 1
end_page = 3



print("=" * 50)
print("PDF CV Extractor for TALASH Project")
print("=" * 50)
print(f"\nInput file: {input_pdf_path}")
print(f"Extracting pages: {start_page} to {end_page}")
print(f"Output file: {output_pdf_path}")
print("\nProcessing...\n")

# Check if input file exists
if not os.path.exists(input_pdf_path):
    print(f" ERROR: File not found at: {input_pdf_path}")
    print("\nPlease update the 'input_pdf_path' variable with the correct path to your data.pdf file")
else:
    extract_pages(input_pdf_path, output_pdf_path, start_page, end_page)