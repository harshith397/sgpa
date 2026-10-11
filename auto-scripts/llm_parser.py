import os
import json
import time
import re
from pathlib import Path
import ollama
from dotenv import load_dotenv
from logger import log_info, log_error, log_warning, log_success

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent


def validate_structure(data):
    if not isinstance(data, list):
        return False
    if not data:
        return True

    for block in data:
        if not isinstance(block, dict):
            return False
        if (
            "PROGRAM" not in block
            or "DEPARTMENT" not in block
            or "SEMESTER" not in block
            or "SUBJECTS" not in block
        ):
            return False
        if not isinstance(block["SUBJECTS"], dict):
            return False

    return True


def process_vision_data(
    input_dir_name: str = "extracted_tables", rate_limit_delay: int = 1
):
    """
    LLM ENGINE (Ollama Local):
    Parses table images to structured JSON using local Ollama model (qwen3.5:4b).
    Returns master_data dictionary on success, or None/False on failure.
    """
    # 1. Ollama Configuration & Client Initialization
    ollama_host = os.getenv("OLLAMA_HOST", "http://192.168.0.8:11434")
    model_name = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")
    ollama_api_key = os.getenv("OLLAMA_API_KEY")
    num_predict = int(os.getenv("OLLAMA_NUM_PREDICT", "4096"))
    temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))

    headers = {}
    if ollama_api_key:
        headers["Authorization"] = f"Bearer {ollama_api_key}"

    try:
        client = ollama.Client(
            host=ollama_host,
            headers=headers if headers else None
        )
        log_info(f"Initialized Ollama Client at '{ollama_host}' using model '{model_name}'.")
    except Exception as e:
        log_error(f"Failed to initialize Ollama client at '{ollama_host}': {e}")
        return None

    # 2. State Initialization
    master_data = {}
    completed_files = set()

    input_path = REPO_ROOT / input_dir_name

    # Check alternative path if not directly in REPO_ROOT
    if not input_path.exists():
        alt_path = Path(__file__).resolve().parent / input_dir_name
        if alt_path.exists():
            input_path = alt_path
        else:
            log_error(f"Input directory '{input_path}' does not exist. Halting.")
            return None

    image_files = sorted([f for f in os.listdir(input_path) if f.endswith(".png")])
    total_files = len(image_files)

    if total_files == 0:
        log_warning(f"No PNG table images found in '{input_path}'. Exiting.")
        return None

    log_info(f"Located {total_files} table images to parse.")

    # 3. Execution Loop
    for index, filename in enumerate(image_files, 1):
        if filename in completed_files:
            continue

        image_file_path = input_path / filename
        log_info(f"[{index}/{total_files}] Parsing: {filename}")

        # Dynamic System Prompt injecting filename as fallback context
        system_prompt = f"""You are a strict data extraction parser. Extract academic syllabus details from the table in the image into a specific JSON object structure.

FALLBACK CONTEXT: If the image lacks explicit headers for the department or semester, use the filename '{filename}' as secondary context to deduce them. CRITICAL: The visual information inside the image ALWAYS takes absolute priority over the filename. Only use the filename if the image data is ambiguous. 

CONTEXTUAL FILTERING RULE: If the table represents non-academic schedules (sports, library, fees, hostel), ignore it and return an empty data array: {{"data": []}} 

STATIC MAPPING RULES (CRITICAL): 
1. PROGRAM: Must be strictly "B.E" or "M.E". 
2. DEPARTMENT: You must map any abbreviations to these exact strings ONLY: 
- "CIVIL ENGINEERING"(it may refered as Civil(case incensitive) in image ) 
- "COMPUTER SCIENCE AND ENGINEERING" (it may refered as cse(case incensitive) in image) 
- "COMPUTER SCIENCE AND ENGINEERING (AI & ML)"(it may refered as csm(case incensitive) in image) 
- "MECHANICAL ENGINEERING"(it may refered as mech(case incensitive) in image) 
- "ELECTRONICS AND COMMUNICATION ENGINEERING" (it may refered as ece(case incensitive) in image) 
- "ELECTRICAL AND ELECTRONICS ENGINEERING"(it may refered as eee(case incensitive) in image) 
- "INFORMATION TECHNOLOGY"(it may refered as it(case incensitive) in image) 
- SPECIALIZATION RULE: If the table is for an Honours degree or specialization (e.g., "Honours Degree in System on Chip Design"), the DEPARTMENT must remain the base department ONLY (e.g., "ELECTRONICS AND COMMUNICATION ENGINEERING"). However, you MUST append the specialization name to the end of EVERY SUBJECT NAME in that table separated by a hyphen. 

3. SEMESTER: MUST be exactly ONE of these strings: "1", "2", "3", "4", "5", "6", "7", or "8". 
- NO RANGES OR TEXT: You are STRICTLY FORBIDDEN from returning values like "5 to 7", "1-2", "V", or "Sem 1". 
- SPANNING SEMESTERS: If a table or row spans multiple semesters (e.g., "V to VII" or "5 to 7"), you MUST split this range into individual semesters (e.g., "5", "6", "7"). For EACH semester in that range, create a completely separate, duplicate object inside the "data" array containing that semester's individual integer string and the exact same subjects. Do NOT output ranges like "5 to 7" as the SEMESTER value. 
- MULTIPLE DISTINCT SEMESTERS: If a table lists different semesters row-by-row, group them and create a separate object in the JSON array for EACH distinct semester. 

4. CREDITS: If blank or '-', output "0". 

OUTPUT SCHEMA FORMAT: You MUST return a JSON object with a single root key called "data". The value of "data" must be an array of objects. 
{{ 
  "data": [ 
    {{ 
      "PROGRAM": "B.E", 
      "DEPARTMENT": "CIVIL ENGINEERING", 
      "SEMESTER": "1", 
      "SUBJECTS": {{ 
        "SUBJECT NAME IN UPPERCASE": {{ 
          "COURSE CODE": "string", 
          "CREDITS": "string" 
        }} 
      }} 
    }} 
  ] 
}} 

Return ONLY valid JSON matching this exact schema. No markdown formatting blocks, no explanations."""

        retry_count = 0
        max_retries = 3
        processing_complete = False

        while not processing_complete:
            try:
                response = client.chat(
                    model=model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": system_prompt,
                            "images": [str(image_file_path)],
                        }
                    ],
                    options={
                        "temperature": temperature,
                        "num_predict": num_predict,
                    },
                    think=False,
                )

                # Extract response text safely across different client return shapes
                if hasattr(response, "message") and hasattr(response.message, "content"):
                    raw_output = response.message.content
                elif isinstance(response, dict) and "message" in response:
                    raw_output = response["message"]["content"]
                else:
                    raw_output = str(response)

                raw_output = raw_output.strip()

                # Clean thinking trace if leaked in content
                raw_output = re.sub(r"<think>[\s\S]*?</think>", "", raw_output).strip()

                # Strip markdown code blocks if the model wrapped output in fences
                if "```" in raw_output:
                    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_output)
                    if match:
                        raw_output = match.group(1).strip()
                    else:
                        raw_output = raw_output.replace("```json", "").replace("```", "").strip()

                extracted_json = json.loads(raw_output)

                # --- DATA NORMALIZATION PEELER ---
                data_list = []
                if isinstance(extracted_json, dict):
                    if "data" in extracted_json and isinstance(extracted_json["data"], list):
                        data_list = extracted_json["data"]
                    else:
                        for key, value in extracted_json.items():
                            if isinstance(value, list):
                                data_list = value
                                break

                # --- SCHEMA VALIDATION ---
                if not validate_structure(data_list):
                    log_error(f"Structural Validation Failed for '{filename}': Invalid schema returned by model.")
                    return False

                # --- DATA INJECTION ---
                total_extracted_subs = 0
                if data_list:
                    for block in data_list:
                        prog = block["PROGRAM"]
                        dept = block["DEPARTMENT"]
                        sem = block["SEMESTER"]
                        subs = block["SUBJECTS"]

                        if prog not in master_data:
                            master_data[prog] = {}
                        if dept not in master_data[prog]:
                            master_data[prog][dept] = {}
                        if sem not in master_data[prog][dept]:
                            master_data[prog][dept][sem] = {}

                        for sub_name, sub_details in subs.items():
                            master_data[prog][dept][sem][sub_name] = sub_details
                            total_extracted_subs += 1

                # Save single image JSON to file for live inspection
                current_output_path = REPO_ROOT / "current_image_output.json"
                try:
                    with open(current_output_path, "w", encoding="utf-8") as f:
                        json.dump(extracted_json, f, indent=2, ensure_ascii=False)
                except Exception as io_err:
                    log_warning(f"Failed to write current_image_output.json: {io_err}")

                completed_files.add(filename)
                processing_complete = True
                log_info(f"  -> Extracted {total_extracted_subs} subject(s). Merged into memory.")

                # Rest GPU between image runs
                gpu_rest_delay = int(os.getenv("GPU_REST_DELAY", rate_limit_delay))
                if gpu_rest_delay > 0:
                    time.sleep(gpu_rest_delay)

            except Exception as e:
                error_str = str(e)
                retry_count += 1
                if retry_count <= max_retries:
                    log_warning(f"Error on '{filename}': {e} | Retrying in 1s (Attempt {retry_count}/{max_retries})...")
                    time.sleep(1)
                else:
                    log_error(f"Persistent failure on '{filename}' after {max_retries} retries: {error_str}")
                    return False

    # 4. Final Success Log
    log_success(f"LLM compilation engine complete! Parsed all {total_files} table images cleanly using '{model_name}'.")
    return master_data


if __name__ == "__main__":
    process_vision_data()
