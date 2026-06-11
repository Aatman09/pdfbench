import os
from pdf2image import convert_from_path

def rasterize_pdf(pdf_path, output_dir, dpi=300):
    """
    Converts a PDF into high-resolution images suitable for computer vision tasks.
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract the base filename without the extension
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    print(f"Processing '{base_name}' at {dpi} DPI...")

    try:
        # Convert PDF pages to a list of PIL Image objects
        pages = convert_from_path(pdf_path, dpi=dpi)

        saved_paths = []
        for i, page in enumerate(pages):
            # Save as PNG for lossless quality, which is critical for OCR
            output_file = os.path.join(output_dir, f"{base_name}_page_{i+1}.png")
            page.save(output_file, "PNG")
            saved_paths.append(output_file)
            print(f" -> Saved: {output_file}")
            
        return saved_paths

    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return []

# Execution block
if __name__ == "__main__":
    # Your specific medical leaflets
    pdf_files = [
        "data/new_data/22201549-Ptd.Leaf.Potass.Phos-CS.pdf",
        "data/new_data/Leaflet Brimonidine TartrateTimolol Maleate Ophthalmic Solution - Caplin.pdf",
        "data/new_data/Leaflet- Ketorolac Trome Inj USP.pdf",
        "data/new_data/Leaflet Nicard inj -CS. 1.pdf"
    ]
    
    # Directory to store the high-res tensors/images
    output_folder = "./processed_leaflets_300dpi"
    
    for pdf in pdf_files:
        if os.path.exists(pdf):
            # 300 DPI is the standard baseline. Push to 600 if the OCR struggles 
            # with the extremely small artwork metadata.
            rasterize_pdf(pdf, output_folder, dpi=600)
        else:
            print(f"File not found in current directory: {pdf}")