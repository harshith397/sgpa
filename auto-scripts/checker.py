import json
import os
from datetime import datetime
from pathlib import Path
from logger import log_info, log_error, log_warning, log_success


def run_initial_state_check():
    """
    Validates state.json to determine if the pipeline should run for the current year.
    Returns target_academic_year (str) if ready to run, or False if completed/lagged.
    """
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    state_file_path = repo_root / "public" / "state.json"

    # 1. State File Existence Check
    if not os.path.exists(state_file_path):
        log_error(f"State file not found at: {state_file_path}")
        log_error("Please create a 'public/state.json' file with initial values. Execution halted.")
        return False

    try:
        with open(state_file_path, "r", encoding="utf-8") as f:
            state_data = json.load(f)
    except json.JSONDecodeError as e:
        log_error(f"Failed to parse JSON from {state_file_path}: {e}")
        return False

    target_academic_year = state_data.get("target_academic_year")
    if not target_academic_year:
        log_error("'target_academic_year' key missing in state.json.")
        return False

    # 2. Extract Years
    try:
        # Splits "20XX-20XY" and grabs integer 20XX
        target_start_year = int(target_academic_year.split("-")[0])
    except (ValueError, IndexError):
        log_error(f"Invalid target academic year format: '{target_academic_year}'. Expected YYYY-YYYY.")
        return False

    current_system_year = datetime.now().year
    log_info(f"Target Academic Year : {target_academic_year} (Start: {target_start_year})")
    log_info(f"Current System Year  : {current_system_year}")

    # 3. Logic Routing
    # Case A: Target > Current (Already Completed)
    if target_start_year > current_system_year:
        log_info(
            f"Pipeline is waiting for {target_academic_year}. "
            f"Current year ({current_system_year}) is already processed. Exiting cleanly."
        )
        return False

    # Case B: Target == Current (Time to Run)
    elif target_start_year == current_system_year:
        log_success(f"Target year '{target_academic_year}' matches current year. Proceeding to web scraping phase...")
        return target_academic_year

    # Case C: Target < Current (State Lag / Failure)
    else:
        log_error("State lag detected in public/state.json!")
        log_error(f"  Target Year : {target_start_year}")
        log_error(f"  System Year : {current_system_year}")
        log_error("  Meaning     : The pipeline failed to increment during a previous execution.")
        log_error("  Action      : Manual intervention needed. Check state.json.")
        return False


if __name__ == "__main__":
    run_initial_state_check()