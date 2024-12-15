import os
import fitz  # PyMuPDF
import re
import openai
from PyPDF2 import PdfReader
from slugify import slugify
from tkinter import Tk
from tkinter.filedialog import askopenfilename
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Directories for Markdown files and images
CONTENT_DIR = "content/posts"
IMAGES_DIR = "static/images"

# Ensure directories exist
os.makedirs(CONTENT_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

# OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("OpenAI API key not found. Ensure OPENAI_API_KEY is set in the .env file.")

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file and clean unnecessary line breaks."""
    print("Extracting text from PDF...")
    reader = PdfReader(pdf_path)
    raw_text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    
    # Remove unnecessary line breaks
    cleaned_text = re.sub(r'(?<!\n)\n(?!\n)', ' ', raw_text)  # Replace single line breaks with a space
    cleaned_text = re.sub(r'\n{2,}', '\n\n', cleaned_text)      # Preserve paragraph breaks
    
    print("Text extraction complete.")
    return cleaned_text.strip()

def extract_images_from_pdf(pdf_path, output_folder):
    """Extract images from a PDF file and save them to a folder."""
    print("Extracting images from PDF...")
    doc = fitz.open(pdf_path)
    image_files = []

    for i, page in enumerate(doc):
        images = page.get_images(full=True)
        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            ext = base_image["ext"]
            image_filename = os.path.join(output_folder, f"image_{i+1}_{img_index+1}.{ext}")
            with open(image_filename, "wb") as img_file:
                img_file.write(image_bytes)

            # Construct Markdown path (relative to the root of the site)
            markdown_path = f"/images/{os.path.basename(output_folder)}/{os.path.basename(image_filename)}"
            image_files.append(markdown_path)

            print(f"Image saved at: {image_filename}")
            print(f"Markdown image path: {markdown_path}")

    print(f"Image extraction complete. {len(image_files)} images saved.")
    return image_files

def gpt4_format_markdown(text, title, image_files):
    """Use GPT-4 to format text into Markdown with front matter and place images in context."""
    from datetime import datetime
    print("Sending text and image data to GPT-4 for Markdown formatting...")
    current_date = datetime.now().strftime("%Y-%m-%d")

    prompt = (
        f"You are an expert Markdown writer. Format the following text into Markdown and place the images appropriately.\n"
        f"Title: {title}\n"
        f"Include the following front matter header at the top of the response:\n"
        f"---\n"
        f"title: '{title}'\n"
        f"date: '{current_date}'\n"
        f"draft: false\n"
        f"---\n"
        f"Text: {text}\n"
        f"Images: {image_files}\n"
        "Make sure to include the images at logical positions in the text, using proper Markdown syntax."
    )

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are a Markdown formatting assistant."},
                  {"role": "user", "content": prompt}]
    )

    markdown = response["choices"][0]["message"]["content"]
    print("Received formatted Markdown from GPT-4.")
    return markdown


def save_markdown_file(markdown, title):
    """Save Markdown content to a file."""
    slug = slugify(title)
    md_filename = os.path.join(CONTENT_DIR, f"{slug}.md")
    with open(md_filename, "w", encoding="utf-8") as md_file:
        md_file.write(markdown)
    print(f"Markdown file saved: {md_filename}")
    return md_filename

from datetime import datetime

def process_pdf(pdf_path):
    """Process a single PDF file: extract text, images, and save as Markdown."""
    print(f"Processing PDF: {pdf_path}")

    # Assume title is the PDF filename without extension
    title = os.path.splitext(os.path.basename(pdf_path))[0]
    slug = slugify(title)
    image_output_folder = os.path.join(IMAGES_DIR, slug)
    os.makedirs(image_output_folder, exist_ok=True)

    # Extract content
    text = extract_text_from_pdf(pdf_path)
    image_files = extract_images_from_pdf(pdf_path, image_output_folder)

    # Format text and images into Markdown using GPT-4
    markdown = gpt4_format_markdown(text, title, image_files)

    # Save Markdown file
    md_filename = save_markdown_file(markdown, title)

    print(f"Processed '{pdf_path}'\nMarkdown saved: {md_filename}\nImages saved to: {image_output_folder}")

def choose_pdf_file():
    """Prompt the user to select a PDF file using a file dialog."""
    Tk().withdraw()  # Hide the root Tkinter window
    file_path = askopenfilename(filetypes=[("PDF files", "*.pdf")], title="Select a PDF file")
    return file_path

if __name__ == "__main__":
    pdf_file = choose_pdf_file()
    if pdf_file and os.path.exists(pdf_file):
        process_pdf(pdf_file)
    else:
        print("No file selected or file does not exist.")
