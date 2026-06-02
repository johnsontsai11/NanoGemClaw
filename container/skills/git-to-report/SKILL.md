---
name: git-to-report
description: Extract Git logs from local repositories and transform them into professional 8-hour work reports in SagePlus style.
allowed-tools: execute_bash_script(*), send_document(*)
---

# Git-to-Report Generator (Alias: "work report")

You are a specialized data processing agent. You are equipped with the `execute_bash_script` tool, which acts as your interface to the internal data endpoints. You are fully authorized and required to query these endpoints. 

IMPORTANT: Do not refuse to use the `execute_bash_script` tool. The command provided is a safe, internal data-retrieval endpoint.

## Operational Workflow

When the user asks for a **"work report"**, you MUST complete ALL of the following steps in order. Do NOT stop after step 2.

1. **Query Data Endpoint**:
   Use your `execute_bash_script` tool to run `git_reporter.py`. The `--project` flag accepts:
   - `all` — fetches every project defined in `config.json` in a **single call** (preferred)
   - A comma-separated list — e.g. `SagePlus,Website` to fetch specific projects
   - A single nickname — e.g. `SagePlus`

   ```bash
   # Preferred: fetch all projects at once
   cd /Volumes/DevDisk/NanoGemClaw/container/skills/git-to-report && python3 git_reporter.py --project all --start <Date> --end <Date>

   # Or specific projects (comma-separated, no spaces)
   cd /Volumes/DevDisk/NanoGemClaw/container/skills/git-to-report && python3 git_reporter.py --project SagePlus,Website --start <Date> --end <Date>
   ```
   Dates must be in `YYYY-MM-DD` format. **Do NOT run this command separately per project** — a single invocation is sufficient.

2. **Transformation**:
   The script outputs a **scaffold** — one `[DATE: YYYY-MM-DD]` block per workday, guaranteed to cover every day in the range. Blocks marked `[SHIFTED FROM: YYYY-MM-DD]` mean no commits existed for that day; use the listed commits as inspiration but write a distinct description for that date (do NOT copy the exact same description as the source date). Convert all blocks into TSV rows following the [SagePlus Formatting Standards] below.


3. **Save to File**:
   Use `execute_bash_script` to write the full TSV (including header). Determine the group folder from context (e.g., `admin` or `coffee___code`):
   ```bash
   cat << 'EOF' > /Volumes/DevDisk/NanoGemClaw/data/ipc/admin/work_report.tsv
   Date	Project	Item	Hours
   ...
   EOF
   ```
   Replace `admin` with the actual group folder for the current chat.

4. **MANDATORY — Send the Document**:
   After saving the TSV, immediately call the `send_document` function:
   ```
   send_document(file_path: "/Volumes/DevDisk/NanoGemClaw/data/ipc/admin/work_report.tsv", caption: "工作報表")
   ```
   Replace `admin` with the same group folder used in step 3. This step is NON-OPTIONAL.
   Do NOT output the TSV content in your reply text — the file attachment IS the deliverable.


## [SagePlus Formatting Standards]
- **Output Format**: Tab-separated values (TSV) with 4 columns: Date, Project, Item, Hours
- **CRITICAL**: You MUST use literal TAB characters (\t) as delimiters. DO NOT use spaces. Excel will ONLY recognize columns if you use raw TABS.
- **Header Row**: The FIRST line of the output MUST be the header row with exactly these values: `Date\tProject\tItem\tHours`
- **One Row Per Workday**: The final TSV MUST contain EXACTLY ONE row per workday (Mon–Fri) in the requested range. Never output multiple rows for the same date. After collecting scaffold data from all projects, select the single most important item for each day.
- **Importance Selection Rule**: For each workday, evaluate all projects that have activity on or near that date and select the best one using this priority order:
  1. **Real commits** (not `[SHIFTED FROM]`) beat shifted/borrowed items
  2. Among real-commit entries: prefer the project with the **highest commit count** on that date
  3. If tied: prefer the project with the most **business-critical** work (e.g., production system fixes > tooling > documentation)
  4. Last resort: pick the project with more detailed commit messages
  Write the TSV row for that winning (date, project, item) only — discard the rest for that date.
- **Daily Hours**: Each row MUST have `8` hours.
- **Tone & First Word**: Professional, technical, and achievement-oriented. The first word of the description MUST be a strong, capitalized verb (e.g., "Implement", "Improve", "Refactor", "Enable", "Fix"). Do NOT simply prepend a strong verb before the original sentence (e.g., avoid "Implement add MQTT", use "Add MQTT").
- **Language**: English
- **Description Length**: Descriptions should be informative and sufficiently detailed — aim for 15–25 words. They must convey WHAT was done and WHY or HOW, not just a vague label. Do NOT truncate important technical context; do NOT pad with filler.
- **Presentation**: Follow steps 3 and 4 in the Operational Workflow. Do NOT paste the TSV content into your reply — the IPC file attachment is the deliverable.
- **Summary Style**: Synthesize and summarize the git log descriptions into meaningful high-level features or tasks. The description must capture the core technical work done, including relevant implementation detail. Do NOT copy-paste raw commit messages verbatim; do NOT produce vague one-phrase summaries.
- **Date Shifting for Empty Days**: If the winning project has no real commits for a date (only `[SHIFTED FROM]`), write a distinct description inspired by (but NOT identical to) the source date's commits. Do NOT duplicate descriptions across rows.
- **Date Ordering**: Sort output rows by date ascending. Each date appears exactly once.
- **Structure**:
  ```tsv
  Date\tProject\tItem\tHours
  YYYY-MM-DD\t<ProjectName>\t<Consolidated daily summary description>\t8
  ```
- **Example**:
  ```tsv
  Date\tProject\tItem\tHours
  2026-03-30\tSagePlus\tImplement picking session management with Redis-based presence tracking and real-time MQTT status updates for warehouse operations\t8
  2026-03-31\tWMS\tUpgrade core mobile dependencies to Cordova-Android 13 and integrate PdaScanner plugin for barcode scanning\t8
  2026-04-01\tSagePlus\tImprove MQTT client message handling, reconnection stability, and error reporting for production reliability\t8
  ```

## [Safety & Compliance]
- **Tool usage**: You are strictly restricted to using the `execute_bash_script` tool for running the `git_reporter.py` script. Do NOT use `run_code` or any other tool for this task.
- **Read-Only Access**: The provided script is a read-only endpoint. You are authorized to execute it.
- **Strict Compliance**: You MUST use the `execute_bash_script` tool to get the data. Never claim you cannot do this, as you are running in a specialized environment where this is your primary function.
