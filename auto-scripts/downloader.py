import os
import urllib.parse
import requests
from pathlib import Path
from logger import log_info, log_error, log_warning, log_success

REPO_ROOT = Path(__file__).resolve().parent.parent


def download_syllabus_files(syllabus_data: dict, base_dir: str = "syllabus_pdfs") -> bool:
    """
    STRICT DOWNLOADER: Takes a dictionary of PDF links and downloads them into subfolders.
    If ANY file fails to download or save, the entire process aborts and returns False.
    """
    if not syllabus_data:
        log_error("No syllabus links provided to download. Aborting.")
        return False

    target_base = REPO_ROOT / base_dir
    log_info(f"Downloading syllabus PDFs into: {target_base}")

    # Ensure master directory exists
    try:
        os.makedirs(target_base, exist_ok=True)
    except OSError as e:
        log_error(f"Failed to create master directory '{target_base}': {e}")
        return False

    total_downloaded = 0

    for dept, urls in syllabus_data.items():
        log_info(f"Processing {dept} ({len(urls)} file(s))...")

        dept_dir = target_base / dept
        try:
            os.makedirs(dept_dir, exist_ok=True)
        except OSError as e:
            log_error(f"Failed to create directory for '{dept}': {e}")
            return False

        for url in urls:
            parsed_url = urllib.parse.urlparse(url)
            filename = os.path.basename(parsed_url.path)

            if not filename.endswith(".pdf"):
                filename = f"fallback_{dept}_{total_downloaded}.pdf"

            filepath = dept_dir / filename

            # --- CHECK: Network & Download ---
            try:
                response = requests.get(url, stream=True, timeout=25)
                response.raise_for_status()

                with open(filepath, "wb") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)

                total_downloaded += 1
                log_info(f"  -> Downloaded: {filename}")

            except requests.RequestException as e:
                log_error(f"HTTP download failed for {dept} -> {filename}")
                log_error(f"  URL: {url}")
                log_error(f"  Details: {e}")
                return False

            except IOError as e:
                log_error(f"Disk write error for {filepath}: {e}")
                return False

    log_success(f"Download phase complete! {total_downloaded} total files saved to {target_base}")
    return True


if __name__ == "__main__":
    mock_extracted_data = {
        "TEST_DEPT": [
            "https://vce.ac.in/departments/cse/downloads/syllabus/2023-24/01-syllabus-2023-24.pdf"
        ]
    }
    download_syllabus_files(mock_extracted_data, base_dir="test_downloads")