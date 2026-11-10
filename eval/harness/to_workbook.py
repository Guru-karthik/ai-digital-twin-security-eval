"""Write run rows into the workbook's Runs sheet (input columns only; formula columns are left untouched).

Writes a copy by default so the seed workbook is never modified in place.
"""
import json
import shutil

FIELD_MAP = {"run_id": "run_id", "timestamp": "date", "case_id": "case_id", "model": "model", "defense": "defense",
             "run_idx": "run_idx", "temperature": "temperature", "outcome": "success", "tools_called": "tools_called",
             "tokens_in": "tokens_in", "tokens_out": "tokens_out", "latency_s": "latency_s",
             "response_excerpt": "response_excerpt", "notes": "reason"}


def write_runs(workbook, runs_jsonl, out_path, first_row=3):
    import openpyxl

    shutil.copyfile(workbook, out_path)
    wb = openpyxl.load_workbook(out_path)
    ws = wb["Runs"]
    header = {c.value: c.column for c in ws[1]}
    runs = [json.loads(line) for line in open(runs_jsonl, encoding="utf-8") if line.strip()]
    for i, r in enumerate(runs):
        row = first_row + i
        for col, key in FIELD_MAP.items():
            v = r.get(key)
            if col == "outcome":
                v = None if v is None else int(bool(v))
            ws.cell(row=row, column=header[col], value=v)
        if "tool_config" in header:
            ws.cell(row=row, column=header["tool_config"], value=f"T{r.get('tool_config', 0)}")
    wb.save(out_path)
    return len(runs)
