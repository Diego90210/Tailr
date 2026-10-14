# -*- coding: utf-8 -*-
"""Genera feature_list.json a partir de TASKS.md.

TASKS.md es la referencia humana (plan detallado: prioridad, estimacion,
dependencias, trazabilidad). feature_list.json es el archivo operativo que los
agentes leen y actualizan en cada sesion.

Uso:
    python build_feature_list.py --tasks TASKS.md --out feature_list.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

# TASKS.md usa etiquetas en mayusculas; el JSON usa estados maquina en snake_case.
STATUS_MAP = {
    "TODO": "pending",
    "WIP": "in_progress",
    "REVIEW": "review",
    "DONE": "done",
    "BLOCKED": "blocked",
}

VALID_STATUSES = ["pending", "in_progress", "review", "done", "blocked"]

TASK_ID_RE = re.compile(r"^`([A-Z][A-Z0-9]*-\d+)`$")
PRIORITY_RE = re.compile(r"^\**\s*(P[0-3])\s*\**$")


def clean(text: str) -> str:
    """Quita marcado markdown de una celda, conservando el texto."""
    text = text.replace("**", "")
    text = text.replace("`", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_name(text: str) -> str:
    """Normaliza un titulo: sin punto final."""
    return clean(text).rstrip(". ")


def clean_phase(text: str) -> str:
    """Quita el numero de seccion y el enfasis markdown del encabezado."""
    text = re.sub(r"^\d+\.\s*", "", text.strip())
    return text.replace("*", "").strip()


def split_name_detail(cell: str):
    """Separa 'Titulo en negrita: detalle' en (titulo, detalle)."""
    raw = cell.strip()
    m = re.match(r"^\*\*(.+?)\*\*\s*:?\s*(.*)$", raw, re.S)
    if m:
        return clean_name(m.group(1)), clean(m.group(2))
    return clean_name(raw), ""


def split_list(cell: str):
    cell = cell.strip()
    if cell in ("", "—", "-", "n/a"):
        return []
    return [clean(p) for p in cell.split(",") if clean(p)]


def parse_tasks(path: Path):
    features = []
    current_phase = ""
    next_id = 1

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current_phase = clean_phase(line[3:])
            continue
        if not line.startswith("|"):
            continue

        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) != 7:
            continue

        m = TASK_ID_RE.match(parts[0])
        if not m:
            continue

        key = m.group(1)
        name, detail = split_name_detail(parts[1])

        priority = parts[2].replace("*", "").strip()
        if not PRIORITY_RE.match(parts[2]):
            priority = "P2"

        raw_status = parts[3].strip().upper()
        status = STATUS_MAP.get(raw_status)
        if status is None:
            print(f"[WARN] estado desconocido '{raw_status}' en {key}; se usa 'pending'",
                  file=sys.stderr)
            status = "pending"

        estimate = parts[4].strip()
        depends = split_list(parts[5])
        refs = split_list(parts[6])

        acceptance = [detail] if detail else [name]
        acceptance.append("Definition of Done (TASKS.md §19) satisfied")

        features.append({
            "id": next_id,
            "key": key,
            "area": key.split("-")[0],
            "name": name,
            "detail": detail,
            "phase": current_phase,
            "priority": priority,
            "status": status,
            "estimate": estimate,
            "depends_on": depends,
            "refs": refs,
            "acceptance": acceptance,
        })
        next_id += 1

    return features


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="TASKS.md")
    ap.add_argument("--out", default="feature_list.json")
    args = ap.parse_args()

    tasks_path = Path(args.tasks)
    if not tasks_path.is_file():
        print(f"[FAIL] No se encontro {tasks_path}", file=sys.stderr)
        return 1

    features = parse_tasks(tasks_path)

    # Los ids deben ser conocidos para que las dependencias por 'key' resuelvan.
    known = {f["key"] for f in features}
    for f in features:
        f["depends_on_keys"] = [d for d in f["depends_on"] if d in known]
        f["depends_on_ext"] = [d for d in f["depends_on"] if d not in known]

    payload = {
        "project": "Tailr",
        "version": 1,
        "source": "TASKS.md",
        "note": "Operative task list. TASKS.md is the human-readable reference. "
                "Update ONLY this file during a session; regenerate from TASKS.md "
                "if the plan changes structurally.",
        "statuses": VALID_STATUSES,
        "priority_order": ["P0", "P1", "P2", "P3"],
        "rules": {
            "one_active_at_a_time": True,
            "active_statuses": ["in_progress", "review"],
            "choose_next": "lowest priority rank first, then lowest id with satisfied depends_on",
        },
        "counts": {
            "total": len(features),
            "by_status": {s: sum(1 for f in features if f["status"] == s)
                          for s in VALID_STATUSES},
            "by_priority": {p: sum(1 for f in features if f["priority"] == p)
                            for p in ["P0", "P1", "P2", "P3"]},
        },
        "features": features,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")

    print(f"[OK] {out} — {len(features)} features")
    print("     by status:  " + ", ".join(
        f"{s}={payload['counts']['by_status'][s]}" for s in VALID_STATUSES))
    print("     by priority: " + ", ".join(
        f"{p}={payload['counts']['by_priority'][p]}" for p in ["P0", "P1", "P2", "P3"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
