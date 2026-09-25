import os
import re
import fitz  # PyMuPDF
from pathlib import Path
from logger import log_info, log_error, log_warning, log_success

REPO_ROOT = Path(__file__).resolve().parent.parent


def extract_scheme_pages(input_dir: str = "syllabus_pdfs", output_dir: str = "extracted_tables") -> bool:
    """
    SLICING ENGINE: Slices out scheme/index pages and converts them to high-res images.
    Returns True if execution passes flawlessly, False if a critical system failure occurs.
    """
    base_path = REPO_ROOT / input_dir
    target_out_path = REPO_ROOT / output_dir

    try:
        os.makedirs(target_out_path, exist_ok=True)
    except OSError as e:
        log_error(f"Failed to create image output directory '{target_out_path}': {e}")
        return False

    target_phrase = "scheme of instruction and examination"
    bridge_pattern = re.compile(r"bridge\s+courses?", re.IGNORECASE)
    service_pattern = re.compile(r"service\s+courses?", re.IGNORECASE)

    zoom_x, zoom_y = 2.0, 2.0
    mat = fitz.Matrix(zoom_x, zoom_y)

    total_images_extracted = 0
    processed_depts = set()

    pdf_files = sorted(list(base_path.glob("*/*.pdf")))

    if not pdf_files:
        log_error(f"No PDF documents located in '{base_path}/*/*.pdf'")
        return False

    log_info(f"Scanning {len(pdf_files)} PDF(s) for scheme tables across departments...")

    for pdf_path in pdf_files:
        dept_name = pdf_path.parent.name
        file_name = pdf_path.name
        doc_image_count = 0

        try:
            doc = fitz.open(pdf_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text").lower()

                is_target = target_phrase in text
                is_bridge = bool(bridge_pattern.search(text))
                is_service = bool(service_pattern.search(text))

                if is_target and not is_bridge and not is_service:
                    pix = page.get_pixmap(matrix=mat)

                    safe_filename = file_name.replace(".pdf", "")
                    output_filename = f"{dept_name}__{safe_filename}__p{page_num + 1}.png"
                    output_file_path = target_out_path / output_filename

                    pix.save(str(output_file_path))
                    doc_image_count += 1
                    total_images_extracted += 1
                    processed_depts.add(dept_name)

            doc.close()
            if doc_image_count > 0:
                log_info(f"  [{dept_name}] '{file_name}': Sliced {doc_image_count} scheme page(s).")

        except Exception as e:
            log_error(f"PyMuPDF rendering error on {dept_name} -> {file_name}: {e}")
            return False

    if total_images_extracted == 0:
        log_error(f"Scanned all files, but zero pages matched phrase: '{target_phrase}'")
        return False

    log_success(
        f"Image extraction complete! Sliced {total_images_extracted} scheme table(s) "
        f"across {len(processed_depts)} departments into: {target_out_path}"
    )
    return True


if __name__ == "__main__":
    extract_scheme_pages()