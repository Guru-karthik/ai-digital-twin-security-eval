"""Merge reviewed draft batches into the workbook (Attack_Cases / Benign_Cases), keeping case ids stable.

Adds an `oracle_params` column (and `source` on Benign_Cases), extends the Lists values and the data-validation
ranges, and refuses to touch ids that already exist. Run once per approved batch.
"""
import copy
import csv
import sys
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter

from .cases import WORKBOOK

NEW_SOURCE, NEW_ORACLE = "LLM-drafted", "substring/tool check"
NEW_CATEGORIES = ["lead no-intent"]


def _ensure_col(ws, name):
    header = {c.value: c.column for c in ws[1]}
    if name in header:
        return header[name]
    col = ws.max_column + 1
    ws.cell(1, col, name)
    ws.cell(1, col)._style = copy.copy(ws.cell(1, col - 1)._style)
    return col


def _extend_list(wb, list_col_header, value):
    ws = wb["Lists"]
    col = {c.value: c.column for c in ws[1]}[list_col_header]
    vals = [ws.cell(r, col).value for r in range(2, 40)]
    if value in vals:
        return
    row = 2 + sum(v is not None for v in vals)
    ws.cell(row, col, value)._style = copy.copy(ws.cell(row - 1, col)._style)
    letter = get_column_letter(col)
    for sheet in wb:
        for dv in sheet.data_validations.dataValidation:
            if dv.formula1 and dv.formula1.startswith(f"Lists!${letter}$2:${letter}$"):
                dv.formula1 = f"Lists!${letter}$2:${letter}${row}"


def merge(attack_csv, benign_csv, status="reviewed", note=None, path=WORKBOOK):
    wb = openpyxl.load_workbook(path)
    for header, value in (("source", NEW_SOURCE), ("oracle", NEW_ORACLE)):
        _extend_list(wb, header, value)
    for v in NEW_CATEGORIES:
        _extend_list(wb, "benign_category", v)
    added = {}
    for sheet, f in (("Attack_Cases", attack_csv), ("Benign_Cases", benign_csv)):
        ws = wb[sheet]
        _ensure_col(ws, "oracle_params")
        if sheet == "Benign_Cases":
            _ensure_col(ws, "source")
        header = {c.value: c.column for c in ws[1]}
        existing = {ws.cell(r, 1).value for r in range(2, ws.max_row + 1)}
        last = max(r for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value)
        n = 0
        with open(f, newline="", encoding="utf-8") as fh:
            for rec in csv.DictReader(fh):
                if rec["case_id"] in existing:
                    raise ValueError(f"{rec['case_id']} already in {sheet}")
                last += 1
                for c in range(1, ws.max_column + 1):
                    ws.cell(last, c)._style = copy.copy(ws.cell(last - 1, c)._style)
                if "status" in rec:
                    rec["status"] = status
                    if note:
                        rec["notes"] = note
                for k, v in rec.items():
                    if k in header and v != "":
                        ws.cell(last, header[k], v)
                n += 1
        added[sheet] = n
    wb.save(path)
    return added


if __name__ == "__main__":
    d = Path(sys.argv[1])
    print(merge(d / "batch_01_attack.csv", d / "batch_01_benign.csv",
                note="Batch 1: owner approved in bulk on 2026-11-10 without per-row edits"))
