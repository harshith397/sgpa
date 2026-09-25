import re
import urllib.parse
import requests
from bs4 import BeautifulSoup
from logger import log_info, log_error, log_warning, log_success

# Static dictionary of department starting points
DEPARTMENT_URLS = {
    "COMPUTER_SCIENCE_AND_ENGINEERING": "https://vce.ac.in/departments/cse/cse-dept-cse-syllabus.php",
    "COMPUTER_SCIENCE_AND_ENGINEERING_(AI_&_ML)": "https://vce.ac.in/departments/cse/cse-dept-csm-syllabus.php",
    "ELECTRONICS_AND_COMMUNICATION_ENGINEERING": "https://vce.ac.in/departments/ece/ece-dept-syllabus.php",
    "ELECTRICAL_AND_ELECTRONICS_ENGINEERING": "https://vce.ac.in/departments/eee/eee-dept-syllabus.php",
    "INFORMATION_TECHNOLOGY": "https://vce.ac.in/departments/it/it-dept-syllabus.php",
    "MECHANICAL_ENGINEERING": "https://vce.ac.in/departments/mechanical/mech-dept-syllabus.php",
    "CIVIL_ENGINEERING": "https://vce.ac.in/departments/civil/civil-dept-syllabus.php",
}


def extract_syllabus_links(target_academic_year: str) -> dict:
    """
    STRICT EXTRACTOR: Scrapes college portal for syllabus PDFs.
    If ANY department is missing data, structurally changed, or fails to load,
    the entire process aborts and returns an empty dictionary {}.
    """
    log_info(f"Starting syllabus link extraction for academic year: {target_academic_year}")
    extracted_dept_links = {}

    for dept, url in DEPARTMENT_URLS.items():
        log_info(f"Checking portal for {dept}...")

        # --- CHECK 1: Network & Uptime ---
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            log_error(f"Network error while scraping {dept}: {e}")
            log_error(f"  Target URL: {url}")
            log_error("Halting entire extraction to prevent incomplete datasets.")
            return {}

        soup = BeautifulSoup(response.text, "html.parser")

        # --- CHECK 2: Target Year Existence (Partial Upload Check) ---
        year_node = soup.find(
            "button",
            class_="accordion-button",
            string=re.compile(target_academic_year),
        )

        if not year_node:
            log_warning(f"Incomplete college upload: '{target_academic_year}' not found on {dept} page.")
            log_warning("Halting to prevent partial data collection. Waiting for college to upload all departments.")
            return {}

        # --- CHECK 3: DOM Structure Integrity ---
        accordion_item = year_node.find_parent("div", class_="accordion-item")
        if not accordion_item:
            log_error(f"DOM Structure Change in {dept}: Found year '{target_academic_year}' but missing parent '.accordion-item'.")
            log_error("Manual HTML inspection required.")
            return {}

        # --- CHECK 4: PDF Link Validation ---
        pdf_tags = accordion_item.select('a[href$=".pdf"]')
        if not pdf_tags:
            log_error(f"Missing PDF Data in {dept}: Accordion found for '{target_academic_year}', but no .pdf links inside.")
            return {}

        # --- SUCCESS: Normalize and Store ---
        dept_links = []
        for tag in pdf_tags:
            relative_url = tag.get("href")
            absolute_url = urllib.parse.urljoin(url, relative_url)
            dept_links.append(absolute_url)

        extracted_dept_links[dept] = dept_links
        log_success(f"{dept}: Extracted {len(dept_links)} PDF link(s).")

    log_success(f"All {len(DEPARTMENT_URLS)} departments successfully verified and extracted for {target_academic_year}.")
    return extracted_dept_links


if __name__ == "__main__":
    target_year = "2026-2027"
    results = extract_syllabus_links(target_year)
    for d, links in results.items():
        print(f"\n{d} ({len(links)} files):")
        for link in links:
            print(f" - {link}")