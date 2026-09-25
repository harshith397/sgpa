import subprocess
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from logger import log_banner, log_section, log_info, log_error, log_warning, log_success
from checker import run_initial_state_check
from links_extractor import extract_syllabus_links
from downloader import download_syllabus_files
from image_extractor import extract_scheme_pages
from llm_parser import process_vision_data
from verify import verify_syllabus_structure

REPO_ROOT = Path(__file__).resolve().parent.parent


def update_files_before_commit(target_dict_data):
    """
    Overwrites src/data/syllabus.json with the new verified syllabus structure
    and increments the academic year in public/state.json.
    Returns True on success, False on failure.
    """
    try:
        # File 1: Write target data into frontend production path
        prod_json_path = REPO_ROOT / "src" / "data" / "syllabus.json"
        prod_json_path.parent.mkdir(parents=True, exist_ok=True)

        with open(prod_json_path, "w", encoding="utf-8") as f:
            json.dump(target_dict_data, f, indent=2)
        log_success(f"Updated production syllabus data: {prod_json_path}")

        # File 2: Increment Academic Year in state.json
        year_file_path = REPO_ROOT / "public" / "state.json"

        if not year_file_path.exists():
            log_error(f"Cannot find '{year_file_path}' to update academic year.")
            return False

        with open(year_file_path, "r", encoding="utf-8") as f:
            year_data = json.load(f)

        current_year = year_data.get("target_academic_year")
        if not current_year or "-" not in current_year:
            log_error(f"Invalid or missing 'target_academic_year' in state.json: {current_year}")
            return False

        start_year, end_year = current_year.split("-")
        new_academic_year = f"{int(start_year) + 1}-{int(end_year) + 1}"
        year_data["target_academic_year"] = new_academic_year

        with open(year_file_path, "w", encoding="utf-8") as f:
            json.dump(year_data, f, indent=2)

        log_success(f"Incremented academic year: '{current_year}' ➜ '{new_academic_year}' in {year_file_path.name}")
        return True

    except Exception as e:
        log_error(f"Failed to update production files: {e}")
        return False


def run_git_command(command):
    """Executes a git command anchored to REPO_ROOT and logs outputs/errors."""
    try:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.stdout.strip():
            log_info(f"  [git] {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        log_warning(f"Git command failed: {' '.join(command)}")
        if e.stderr.strip():
            log_warning(f"  [git error] {e.stderr.strip()[:300]}")
        return False


def stage_and_commit_locally():
    """
    Stages and commits the updated production files locally.
    Attempts git push, but will not fail the pipeline if push is rejected or unconfigured.
    """
    log_section("Git Version Control")

    state_path = (REPO_ROOT / "public" / "state.json").as_posix()
    syllabus_path = (REPO_ROOT / "src" / "data" / "syllabus.json").as_posix()

    if not run_git_command(["git", "add", state_path, syllabus_path]):
        log_warning("Failed to stage modified files with git.")
        return False

    # Check for actual staged changes
    diff = subprocess.run(["git", "diff", "--staged", "--quiet"], cwd=REPO_ROOT)
    if diff.returncode == 0:
        log_info("No changes detected in syllabus files. Skipping git commit.")
        return True

    # Commit with local git user identity (never alters global configs)
    commit_msg = "chore: update production JSON data and academic year"
    if not run_git_command(["git", "commit", "-m", commit_msg]):
        log_warning("Git commit skipped or failed.")
        return False

    log_success("Git commit created successfully.")

    # Optional Push (safe local push attempt)
    log_info("Attempting 'git push' to remote repository...")
    if run_git_command(["git", "push"]):
        log_success("Git push completed successfully.")
    else:
        log_warning("Git push did not complete. Your local files and commit are saved and safe.")

    return True


def main():
    log_banner("SYLLABUS AUTOMATION PIPELINE (LOCAL RUN)")

    # Step 1: Initial State Check
    log_section("Phase 1: Initial State Check")
    target_year = run_initial_state_check()
    if not target_year:
        log_warning("Pipeline halted at Phase 1 (State Check). Nothing to do.")
        return

    # Step 2: Links Extraction
    log_section("Phase 2: Syllabus Links Scraping")
    extracted_dept_links = extract_syllabus_links(target_year)
    if not extracted_dept_links:
        log_error("Pipeline halted at Phase 2 (Link Extraction failed).")
        return

    # Step 3: PDF Downloader
    log_section("Phase 3: PDF Downloads")
    download_res = download_syllabus_files(extracted_dept_links)
    if not download_res:
        log_error("Pipeline halted at Phase 3 (Download failed).")
        return

    # Step 4: Page Slicing / Table Image Extraction
    log_section("Phase 4: Slicing Scheme Pages to Images")
    schema_pages_res = extract_scheme_pages()
    if not schema_pages_res:
        log_error("Pipeline halted at Phase 4 (Image Extraction failed).")
        return

    # Step 5: Vision LLM Parsing (Ollama Local)
    log_section("Phase 5: LLM Vision Compilation")
    syl_data = process_vision_data()
    if not syl_data:
        log_error("Pipeline halted at Phase 5 (LLM Parsing failed).")
        return

    # Step 6: Strict Structural Verification
    log_section("Phase 6: Structural Verification")
    verification = verify_syllabus_structure(syl_data)
    if not verification:
        log_error("Pipeline halted at Phase 6 (Verification failed).")
        return

    # Step 7: Update Production Files
    log_section("Phase 7: Production File Updates")
    files_updated = update_files_before_commit(syl_data)
    if not files_updated:
        log_error("Pipeline halted at Phase 7 (File updates failed).")
        return

    # Step 8: Version Control
    stage_and_commit_locally()

    log_banner("PIPELINE COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    main()