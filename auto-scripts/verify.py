import json
import os
from logger import log_info, log_error, log_warning, log_success


def verify_syllabus_structure(data: dict) -> bool:
    """
    Validates the strictly defined hierarchical structure of the generated syllabus JSON.
    Ensures all exact required semesters are present in every department, ignoring order.
    For M.E, departments must strictly belong to the allowed list, but all need not be present.
    """
    errors = []

    # Global Allowed Department Set
    allowed_depts = {
        "CIVIL ENGINEERING",
        "COMPUTER SCIENCE AND ENGINEERING",
        "COMPUTER SCIENCE AND ENGINEERING (AI & ML)",
        "MECHANICAL ENGINEERING",
        "ELECTRONICS AND COMMUNICATION ENGINEERING",
        "ELECTRICAL AND ELECTRONICS ENGINEERING",
        "INFORMATION TECHNOLOGY",
    }

    # 1. Root Key Validation
    allowed_programs = {"B.E", "M.E"}
    actual_programs = set(data.keys())
    invalid_programs = actual_programs - allowed_programs

    if invalid_programs:
        errors.append(f"Invalid outer program keys: {invalid_programs}. Only 'B.E' and 'M.E' are allowed.")

    # 2. B.E Structure Validation
    if "B.E" in data:
        be_data = data["B.E"]
        actual_be_depts = set(be_data.keys())

        # Check Departments (All must match exactly and all must be present)
        invalid_be_depts = actual_be_depts - allowed_depts
        if invalid_be_depts:
            errors.append(f"Invalid B.E departments: {invalid_be_depts}")

        missing_be_depts = allowed_depts - actual_be_depts
        if missing_be_depts:
            errors.append(f"Missing mandatory B.E departments: {missing_be_depts}")

        # Check Semesters (Must contain EXACTLY 1 through 8, order doesn't matter)
        allowed_be_sems = {"1", "2", "3", "4", "5", "6", "7", "8"}

        for dept, sems in be_data.items():
            if not isinstance(sems, dict):
                errors.append(f"B.E -> {dept} is not formatted as a dictionary.")
                continue

            actual_sems = set(sems.keys())

            missing_sems = allowed_be_sems - actual_sems
            if missing_sems:
                errors.append(f"B.E -> {dept} is MISSING semesters: {sorted(list(missing_sems))}")

            extra_sems = actual_sems - allowed_be_sems
            if extra_sems:
                errors.append(f"B.E -> {dept} has EXTRA/INVALID semesters: {sorted(list(extra_sems))}")

    # 3. M.E Structure Validation
    if "M.E" in data:
        me_data = data["M.E"]
        actual_me_depts = set(me_data.keys())

        invalid_me_depts = actual_me_depts - allowed_depts
        if invalid_me_depts:
            errors.append(f"Invalid M.E departments: {invalid_me_depts}")

        allowed_me_sems = {"1", "2", "3", "4"}

        for dept, sems in me_data.items():
            if dept in invalid_me_depts:
                continue

            if not isinstance(sems, dict):
                errors.append(f"M.E -> {dept} is not formatted as a dictionary.")
                continue

            actual_sems = set(sems.keys())

            missing_sems = allowed_me_sems - actual_sems
            if missing_sems:
                errors.append(f"M.E -> {dept} is MISSING semesters: {sorted(list(missing_sems))}")

            extra_sems = actual_sems - allowed_me_sems
            if extra_sems:
                errors.append(f"M.E -> {dept} has EXTRA/INVALID semesters: {sorted(list(extra_sems))}")

    # 4. Final Disposition
    if errors:
        log_error("Phase 5 Validation Failed! Found structural errors:")
        for err in errors:
            log_error(f"  • {err}")
        return False

    log_success("Phase 5 Completed: Syllabus JSON structure perfectly matches all schema requirements!")
    return True


if __name__ == "__main__":
    TARGET_JSON = "src/data/syllabus.json"
    if os.path.exists(TARGET_JSON):
        with open(TARGET_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        verify_syllabus_structure(d)