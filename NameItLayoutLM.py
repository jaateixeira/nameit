from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
from PIL import Image
import torch
import fitz

from utils.validators import validate

def extract_info_from_pdf_using_ai_layout_ai_model(pdf_path):
    # Load the PDF
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)  # Load the first page
    pix = page.get_pixmap()
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    # Load the LayoutLMv3 model and processor
    processor = LayoutLMv3Processor.from_pretrained("microsoft/layoutlmv3-base")
    model = LayoutLMv3ForTokenClassification.from_pretrained("microsoft/layoutlmv3-base")

    # Process the image
    encoding = processor(image, return_tensors="pt")

    # Perform inference
    with torch.no_grad():
        outputs = model(**encoding)

    # Decode the predictions
    predictions = outputs.logits.argmax(-1).squeeze().tolist()
    tokens = encoding.tokens()

    # Extract relevant information
    info = {
        "author": "",
        "journal": "",
        "year": "",
        "title": ""
    }

    current_key = None
    for token, pred in zip(tokens, predictions):
        if token in info.keys():
            current_key = token
        elif current_key:
            info[current_key] += token + " "

    # Clean up the extracted information
    for key in info:
        info[key] = info[key].strip()

    return info
