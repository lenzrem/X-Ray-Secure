import PyPDF2
import spacy
import re
import logging
import argparse
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from decimal import Decimal

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load English NLP model
try:
    nlp = spacy.load("en_core_web_sm")
    logger.info("Loaded spaCy model 'en_core_web_sm'")
except OSError:
    logger.error("Failed to load spaCy model. Ensure 'en_core_web_sm' is installed.")
    raise

def anonymize_pdf(input_path, output_path):
    # Main function to anonymise PDF content
    try:
        logger.info(f"Anonymising PDF: {input_path}")
        with open(input_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            if reader.is_encrypted:
                logger.error("PDF is encrypted. Cannot process.")
                raise ValueError("Encrypted PDF")

            writer = PyPDF2.PdfWriter()

            for page_num in range(len(reader.pages)):
                logger.debug(f"Processing page {page_num + 1}")
                page = reader.pages[page_num]
                content = page.extract_text()
                anonymised_content = anonymise_text(content)
                new_page = create_anonymised_page(page, anonymised_content)
                writer.add_page(new_page)

        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        
        logger.info(f"PDF anonymised: {input_path} -> {output_path}")
        return True

    except Exception as e:
        logger.error(f"PDF anonymisation failed: {str(e)}", exc_info=True)
        return False

def create_anonymised_page(original_page, anonymised_content):
    # Create a new page with anonymised content
    new_page = PyPDF2.PageObject.create_blank_page(
        width=float(original_page.mediabox.width),
        height=float(original_page.mediabox.height)
    )
    new_page.merge_page(original_page)
    watermark = create_watermark(anonymised_content, float(original_page.mediabox.width), float(original_page.mediabox.height))
    new_page.merge_page(watermark)
    return new_page

def create_watermark(text, width, height):
    # Create a watermark with anonymised text
    logger.debug("Creating anonymised text watermark")
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=(width, height))
    can.setFont("Helvetica", 10)
    y = height - 20
    for line in text.split('\n'):
        can.drawString(10, y, line)
        y -= 12
    can.save()
    packet.seek(0)
    return PyPDF2.PdfReader(packet).pages[0]

def anonymise_text(text):
    # Anonymise sensitive information in text
    try:
        logger.debug("Anonymising text")
        doc = nlp(text)

        # Patterns for sensitive data
        patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
        }

        # Replace named entities
        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG']:
                text = text.replace(ent.text, f"[{ent.label_}]")

        # Replace patterns
        for key, pattern in patterns.items():
            text = re.sub(pattern, f'[{key.upper()}]', text)

        # Replace confidential terms
        confidential_terms = ['confidential', 'secret', 'internal use only', 'proprietary']
        for term in confidential_terms:
            text = re.sub(r'\b' + re.escape(term) + r'\b', '[CONFIDENTIAL]', text, flags=re.IGNORECASE)

        logger.debug("Text anonymisation complete")
        return text
    except Exception as e:
        logger.error(f"Text anonymisation error: {str(e)}", exc_info=True)
        return text

def preview_anonymized_pdf(input_path):
    # Generate a preview of anonymised PDF content
    try:
        logger.info(f"Generating PDF preview: {input_path}")
        with open(input_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            if reader.is_encrypted:
                logger.error("PDF is encrypted. Cannot process.")
                raise ValueError("Encrypted PDF")

            preview_text = ""
            for page_num in range(len(reader.pages)):
                logger.debug(f"Processing preview for page {page_num + 1}")
                content = reader.pages[page_num].extract_text()
                preview_text += f"--- Page {page_num + 1} ---\n{content}\n\n"

            anonymizd_preview = anonymize_text(preview_text)
            logger.info("Preview generation successful")
            return anonymized_preview

    except Exception as e:
        logger.error(f"Preview generation failed: {str(e)}", exc_info=True)
        return f"Error: Preview generation failed. {str(e)}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Anonymise PDF files or generate previews.")
    parser.add_argument("input_pdf", help="Path to the input PDF file")
    parser.add_argument("-o", "--output", help="Path to the output anonymised PDF file")
    parser.add_argument("-p", "--preview", action="store_true", help="Generate a preview instead of anonymising")
    
    args = parser.parse_args()

    if args.preview:
        preview = preview_anonymized_pdf(args.input_pdf)
        print("Preview of anonymised content:")
        print(preview)
    else:
        if not args.output:
            print("Error: Output path required for full anonymisation. Use -o or --output option.")
        else:
            success = anonymize_pdf(args.input_pdf, args.output)
            print("PDF anonymised successfully." if success else "PDF anonymisation failed. Check logs for details.")