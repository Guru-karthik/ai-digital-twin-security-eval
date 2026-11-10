"""Load attack and benign cases from the workbook; export JSONL/CSV so the harness never needs Excel at run time."""
import csv
import json
import re
from pathlib import Path

WORKBOOK = Path(__file__).resolve().parents[1] / "cases" / "digital_twin_attack_cases.xlsx"
CASES_JSONL = WORKBOOK.with_name("attack_cases.jsonl")
BENIGN_JSONL = WORKBOOK.with_name("benign_cases.jsonl")

_QUOTED = re.compile(r"'(.+)'", re.S)
_TRIGGER = re.compile(r"(?:Trigger(?: question)?|Ask|Then ask):\s*(.+)$", re.S)


def tool_config_rank(tc: str | None) -> int:
    """Workbook says T0..T3; the code calls them TC0..TC3 to avoid clashing with threat ids."""
    m = re.search(r"(\d)", tc or "T0")
    return int(m.group(1)) if m else 0


def _rows(ws):
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    return [dict(zip(header, r)) for r in rows[1:] if r[0]]


def load_workbook_cases(path=WORKBOOK):
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=False)
    return _rows(wb["Attack_Cases"]), _rows(wb["Benign_Cases"])


def split_script(payload: str) -> list[str]:
    """'1) a 2) b' -> ['a','b']; otherwise a single turn."""
    parts = re.split(r"(?:^|\s)\d\)\s+", payload.strip())
    parts = [p.strip() for p in parts if p.strip()]
    return parts if len(parts) > 1 else [payload.strip()]


def parse_case(row: dict, overrides: dict | None = None) -> dict:
    """Derive the structured fields the runner needs. Anything unparseable is flagged, never guessed."""
    cid = row["case_id"]
    payload = str(row.get("payload_or_script") or "")
    ep = row.get("entry_point")
    case = {
        "case_id": cid, "type": "attack", "class": row.get("class"), "threat_id": row.get("threat_id"),
        "entry_point": ep, "adversary": row.get("adversary"), "oracle": row.get("oracle"),
        "success_criterion": row.get("success_criterion"), "source": row.get("source"),
        "split": row.get("split"), "tool_config": tool_config_rank(row.get("min_tool_config")),
        "parent": None, "mutator": None, "turns": [], "planted_summary": None, "tool_results": {},
        "params": json.loads(row.get("oracle_params") or "{}"),
        "payload": payload, "parse_status": "ok",
    }
    quoted = _QUOTED.search(payload)
    trig = _TRIGGER.search(payload)
    if ep == "E3" and payload.startswith("Planted") and quoted and trig:
        case["planted_summary"] = quoted.group(1)
        case["turns"] = [trig.group(1).strip()]
    elif ep == "E5" and payload.startswith("Mock tool result") and quoted:
        case["tool_results"] = {"record_unknown_question": quoted.group(1)}
        case["turns"] = ["What is your favourite food?"]  # benign unanswerable question triggers the tool
    elif ep in ("E1", "E2", "E4"):
        case["turns"] = split_script(payload)
    else:
        case["parse_status"] = "needs_fixture_or_override"
    if overrides and cid in overrides:
        case.update(overrides[cid])
        case["parse_status"] = "override"
    return case


def parse_benign(row: dict) -> dict:
    return {"case_id": row["case_id"], "type": "benign", "category": row.get("category"),
            "turns": [str(row.get("question_or_script") or "")], "expected": row.get("expected_behavior"),
            "split": row.get("split"), "tool_config": 0 if "tool use" not in str(row.get("category")) else 1,
            "oracle": row.get("oracle"), "parse_status": "ok",
            "params": json.loads(row.get("oracle_params") or "{}"), "source": row.get("source")}


def load_drafts(directory=WORKBOOK.parent / "drafts"):
    """Parsed draft cases not yet in the exported workbook (merged batches are skipped) from batch_*_attack.csv / batch_*_benign.csv. Not in the workbook yet."""
    att, ben = [], []
    for f in sorted(Path(directory).glob("batch_*_attack.csv")):
        with open(f, newline="", encoding="utf-8") as fh:
            att += [parse_case(r) for r in csv.DictReader(fh)]
    for f in sorted(Path(directory).glob("batch_*_benign.csv")):
        with open(f, newline="", encoding="utf-8") as fh:
            ben += [parse_benign(r) for r in csv.DictReader(fh)]
    merged = {c["case_id"] for c in load_jsonl(CASES_JSONL)} | {c["case_id"] for c in load_jsonl(BENIGN_JSONL)} \
        if CASES_JSONL.exists() and BENIGN_JSONL.exists() else set()
    return [c for c in att if c["case_id"] not in merged], [c for c in ben if c["case_id"] not in merged]


def export(path=WORKBOOK, overrides=None):
    att, ben = load_workbook_cases(path)
    cases = [parse_case(r, overrides) for r in att]
    benign = [parse_benign(r) for r in ben]
    for out, data in ((CASES_JSONL, cases), (BENIGN_JSONL, benign)):
        with open(out, "w", encoding="utf-8") as f:
            for c in data:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
    with open(CASES_JSONL.with_suffix(".csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["case_id", "class", "threat_id", "entry_point", "adversary", "oracle",
                                          "split", "source", "tool_config", "parse_status"], extrasaction="ignore")
        w.writeheader()
        w.writerows(cases)
    return cases, benign


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


if __name__ == "__main__":
    c, b = export()
    print(f"exported {len(c)} attack cases, {len(b)} benign cases")
    print("unparsed:", [x["case_id"] for x in c if x["parse_status"] != "ok"])
