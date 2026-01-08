import csv
import os
from collections import defaultdict

INPUT_TSV = "ui/docs/workbench/tsv_import/platform_scopes.tsv"
OUTPUT_BACKLOG = "ui/docs/workbench/tsv_import/CONNECTOR_IMPORT_BACKLOG.tsv"

def generate_backlog():
    # 1. Read Platform Scopes
    platforms = defaultdict(list)
    try:
        with open(INPUT_TSV, "r") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                pid = row["platform_id"]
                platforms[pid].append(row["scope_id"])
    except FileNotFoundError:
        print(f"File not found: {INPUT_TSV}")
        return

    # 2. Add P0 Models (Missing TSV rows)
    # Gemini, Jules
    # We will simulate them being "found" or just add them as tasks.
    backlog_rows = []
    
    # Task ID Counter
    task_idx = 1
    
    # P0 Tasks
    p0_models = ["gemini", "jules"]
    for model in p0_models:
        row = {
            "task_id": f"TASK_{task_idx:03d}_{model.upper()}",
            "priority": "P0",
            "platform_id": model,
            "tool_id": model,
            "batch_id": f"{model}-01",
            "scopes_in_batch": "ALL_SCOPES (Missing TSV)",
            "description": f"Seed {model} connector draft",
            "acceptance_criteria": "Draft appears in Workbench with secret placeholders",
            "inputs": "Manual / Missing TSV"
        }
        backlog_rows.append(row)
        task_idx += 1

    # P1 Tasks (From TSV)
    for pid, scopes in platforms.items():
        # Chunk into batches of 15
        batch_size = 15
        for i in range(0, len(scopes), batch_size):
            batch_scopes = scopes[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            row = {
                "task_id": f"TASK_{task_idx:03d}_{pid.upper()}",
                "priority": "P1",
                "platform_id": pid,
                "tool_id": pid,
                "batch_id": f"{pid}-{batch_num:02d}",
                "scopes_in_batch": ",".join(batch_scopes),
                "description": f"Import {pid} scopes batch {batch_num}",
                "acceptance_criteria": "Scopes present in tool definition",
                "inputs": INPUT_TSV
            }
            backlog_rows.append(row)
            task_idx += 1

    # 3. Write Backlog
    headers = ["task_id", "priority", "platform_id", "tool_id", "batch_id", "scopes_in_batch", "description", "acceptance_criteria", "inputs"]
    
    with open(OUTPUT_BACKLOG, "w") as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter="\t")
        writer.writeheader()
        writer.writerows(backlog_rows)

    print(f"Generated {OUTPUT_BACKLOG}")

if __name__ == "__main__":
    generate_backlog()
