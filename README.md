# VCE SGPA Calculator

A static site SGPA calculator designed for the students of Vasavi College of Engineering.

## Live Demo
https://harshith397.github.io/sgpa/

## Key Features

* **Algorithmic Efficiency:** Utilizes a one-time $O(N)$ JSON flattening parser on load, and an $O(1)$ Hash Map to track grade slider updates, ensuring zero UI thread blocking.
* **Opt-Out Selection UX:** Automatically populates the core subjects for a selected semester, allowing students to remove unused electives/subjects rather than manually adding every course.
* **Zero Backend:** 100% static architecture.

## Tech Stack

* **Core:** React 18
* **Build Tool:** Vite (Native ES Modules for instantaneous HMR)
* **Styling:** Vanilla CSS (CSS Variables, Flexbox, Media Queries)
* **Data:** Local JSON payload (Normalized at runtime)

## Architecture & State Management

Instead of traversing a deeply nested JSON tree (`Program -> Dept -> Sem -> Subject`) on every user interaction, the app employs a **Normalization Strategy**. 

1. **The Parser:** Flattens the hierarchical syllabus data into a single 1D array of subject objects.
2. **Cascading State:** Upstream dropdowns (Program) explicitly invalidate and wipe downstream states (Semester, Grades) to prevent data collisions and mathematically impossible SGPA outputs.
3. **Identifier Safety:** Uses a two-pass Regex Title Case formatter and relies on `subject.name` as the primary key to prevent identifier collisions among open electives that share placeholder course codes.
4. **Automation Pipeline:** The syllabus dataset is updated through `auto-scripts/trigger.py`, which is executed by GitHub Actions.

## Syllabus Data Automation

The repository includes a fully automated syllabus update flow that keeps the local JSON data in sync with the college portal.

1. **GitHub Actions trigger:** `.github/workflows/automation.yml` supports both manual dispatch and a scheduled run. The schedule is configured to run daily at `11:00 UTC` during August.
2. **Python execution environment:** The workflow checks out the repository, installs Python `3.12`, and installs dependencies from `requirements.txt`.
3. **Pipeline entrypoint:** The workflow runs `python auto-scripts/trigger.py` from the repository root.
4. **Data collection steps:** The script chain validates the current academic year, extracts syllabus links, downloads the PDFs, slices the scheme pages into images, parses them with the Groq vision model, and verifies the final JSON structure.
5. **Output update:** On success, the pipeline writes the refreshed syllabus data to `src/data/syllabus.json`, increments `public/state.json`, and pushes the changes back to the repository with a bot commit.
6. **Notifications and secrets:** Discord webhook alerts are sent during success and failure states, and the workflow reads `DISCORD_WEBHOOK_URL`, `GROQ_API_KEY_1`, and `GROQ_API_KEY_2` from GitHub Secrets.

## Local Development Setup

To run this project locally:

1. **Clone the repository:**
   ```bash
   git clone 
   https://github.com/harshith397/sgpa.git
   cd vce-sgpa-calc
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the Vite development server:**
   ```bash
   npm run dev
   ```

4. **Build for production:**
   ```bash
   npm run build
   ```

## Author
**Medichelme Harshith** Computer Science Engineering Undergraduate - Vasavi College of Engineering