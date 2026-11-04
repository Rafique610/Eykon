#!/usr/bin/env python3
"""Check the walkthrough's flow data against its docs (ANALYSIS.md, Phase 3).

    python3 docs/walkthrough/validate_flow.py                      every stage file, then the index
    python3 docs/walkthrough/validate_flow.py --stage s04-scene    one stage, while it is being written
    python3 docs/walkthrough/validate_flow.py --anchors stages/s04-scene.md    a doc's link anchors

Checks: each JSON matches flow/schema.json (no empty text, no bare "n/a"); node ids are unique, start
with their stage id, and owners define their shared ids (notes/file-map.md); edges join existing nodes
and touch their own stage; every "doc" anchor exists in the node's own stage doc; the doc has the eight
sections, its §6 files exist and are in a node, and every primary file has a §6 entry; UNKNOWN decisions
name a question the doc asks. Full run only: every .kt / .py path cited in a stage doc is in some node,
every stage file exists, and the index matches the stage files and has joined traces.
Exit status 1 when anything fails. Standard library only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent  # docs/walkthrough
ROOT = HERE.parents[1]  # the repository
SCHEMA = json.loads((HERE / "flow" / "schema.json").read_text(encoding="utf-8"))
SECTIONS = ["1. Purpose and trigger", "2. Input", "3. Processing, step by step", "4. Models and algorithms used",
            "5. Output", "6. File reference", "7. Design decisions", "8. Open questions"]
ABBREVIATIONS = {"A/": "android/app/src/main/java/com/eykon/memory/",
                 "UT/": "android/app/src/test/java/com/eykon/memory/",
                 "AT/": "android/app/src/androidTest/java/com/eykon/memory/"}
QUESTION = re.compile(r"\bQ-s\d{2}-\d+\b")
CITED_PATH = re.compile(r"`((?:android|src|tests|scratch)/[^`\s:]+\.(?:kt|py)|[A-Za-z_]+\.py)(?::[\d-]+)?`")  # code files only
errors: list[str] = []


def err(where: str, message: str) -> None:
    errors.append(f"{where}: {message}")


# ---- the subset of JSON Schema that flow/schema.json uses ----

def resolve(schema: dict) -> dict:
    while "$ref" in schema:
        schema = SCHEMA["$defs"][schema["$ref"].rsplit("/", 1)[-1]]
    return schema


def check(value, schema: dict, path: str) -> None:
    schema = resolve(schema)
    kind = {"object": dict, "array": list, "string": str}.get(schema.get("type"))
    if kind and not isinstance(value, kind):
        return err(path, f"should be a {schema['type']}")
    if "const" in schema and value != schema["const"]:
        err(path, f"should be {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        err(path, f"{value!r} is not one of {schema['enum']}")
    if isinstance(value, str):
        if schema.get("minLength") and not value.strip():
            err(path, "is empty")
        elif re.fullmatch(r"(?i)\s*n/?a\.?\s*", value):
            err(path, 'is a bare "n/a"; write "n/a: <why>"')
        if "pattern" in schema and not re.search(schema["pattern"], value):
            err(path, f"{value!r} does not match {schema['pattern']}")
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            err(path, f"needs at least {schema['minItems']} item(s)")
        for i, item in enumerate(value):
            check(item, schema.get("items", {}), f"{path}[{i}]")
    elif isinstance(value, dict):
        props, extra = schema.get("properties", {}), schema.get("additionalProperties", True)
        for name in schema.get("required", []):
            if name not in value:
                err(path, f"missing '{name}'")
        for name, item in value.items():
            if name in props:
                check(item, props[name], f"{path}.{name}")
            elif extra is False:
                err(path, f"unknown field '{name}'")
            elif isinstance(extra, dict):
                check(item, extra, f"{path}.{name}")


# ---- markdown ----

def slug(title: str) -> str:
    """GitHub-style anchor: lower case, keep a-z 0-9 space _ -, spaces become hyphens."""
    return re.sub(r"[^a-z0-9 _-]", "", title.strip().lower()).replace(" ", "-")


def headings(text: str) -> list[tuple[int, str]]:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    found, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        elif not fenced and (m := re.match(r"(#{1,6})\s+(.+?)\s*#*\s*$", line)):
            found.append((len(m.group(1)), m.group(2)))
    return found


def anchors(text: str) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for _, title in headings(text):
        base = slug(title)
        out.append(f"{base}-{seen[base]}" if base in seen else base)
        seen[base] = seen.get(base, 0) + 1
    return out


def file_entries(text: str) -> list[str]:
    """The paths of the level-3 headings in §6 File reference."""
    paths, inside = [], False
    for level, title in headings(text):
        if level == 2:
            inside = title.startswith("6.")
        elif inside and level == 3 and (m := re.fullmatch(r"`([^`]+)`", title)):
            paths.append(m.group(1))
    return paths


def file_map() -> tuple[dict[str, list[str]], dict[str, str]]:
    """Primary files per stage, and shared node id -> owning stage, read from notes/file-map.md."""
    body, shared_part = (HERE / "notes" / "file-map.md").read_text(encoding="utf-8").split("## Shared node ids", 1)
    primary: dict[str, list[str]] = {}
    stage, listing = None, False
    for line in body.splitlines():
        if m := re.match(r"## (s\d{2}-[a-z0-9-]+):", line):
            stage, listing = m.group(1), False
            primary[stage] = []
        elif line.startswith("## "):
            stage = None
        elif line.startswith("Primary:"):
            listing = True
        elif line and not line.startswith("- "):
            listing = False
        elif stage and listing and (m := re.match(r"- `([^`]+)`", line)):
            path = m.group(1)
            for short, full in ABBREVIATIONS.items():
                if path.startswith(short):
                    path = full + path[len(short):]
            primary[stage].append(path)
    shared = {m.group(1): m.group(1).split("/")[0]
              for m in re.finditer(r"^\| `(s\d{2}-[a-z0-9-]+/[^`]+)` \|", shared_part, re.M)}
    return primary, shared


# ---- stage files ----

def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        err(str(path.relative_to(HERE)), f"cannot read: {e}")
        return None


def nodes_of(data: dict) -> list[dict]:
    return [data["stage"]] + data.get("nodes", []) if isinstance(data.get("stage"), dict) else data.get("nodes", [])


def check_stage(sid: str, data: dict, every: dict[str, dict], primary: dict, shared: dict, partial: bool) -> None:
    where, md_where = f"flow/stages/{sid}.json", f"stages/{sid}.md"
    check(data, SCHEMA["$defs"]["stage_file"], where)
    stage = data.get("stage") if isinstance(data.get("stage"), dict) else {}
    if stage.get("id") != sid or stage.get("type") != "stage":
        err(where, f"'stage' must be the type 'stage' node with id '{sid}'")
    for name in ("platform", "entry", "exit"):
        if not stage.get(name):
            err(where, f"stage node needs '{name}'")
    md_file = HERE / md_where
    md = md_file.read_text(encoding="utf-8") if md_file.exists() else ""
    if not md:
        err(md_where, "missing")
    marks = set(anchors(md))
    if [t for level, t in headings(md) if level == 2 and t in SECTIONS] != SECTIONS:
        err(md_where, "the eight numbered '##' sections are missing, renamed or out of order")
    own = nodes_of(data)
    for n in own:
        nid = n.get("id", "?")
        if n.get("stage") != sid or nid.split("/")[0] != sid:
            err(where, f"{nid}: belongs to stage {n.get('stage')!r}, this file is {sid}")
        doc, _, anchor = n.get("doc", "").partition("#")
        if doc != md_where:
            err(where, f"{nid}: doc should link into {md_where}")
        elif anchor not in marks:
            err(where, f"{nid}: anchor #{anchor} not found in {md_where} (see --anchors {md_where})")
        for f in n.get("files", []):
            if not (ROOT / f).exists():
                err(where, f"{nid}: file {f} does not exist")
        decision = n.get("decision", {})
        if isinstance(decision, dict) and decision.get("tag") == "UNKNOWN":
            asked = QUESTION.findall(decision.get("source", ""))
            if not asked or any(q not in md for q in asked):
                err(where, f"{nid}: UNKNOWN decision must name a question id that {md_where} asks")
    for end in stage.get("entry", []) + stage.get("exit", []):
        if end not in every:
            err(where, f"stage entry/exit {end} is not a node")
    for nid, owner in shared.items():
        if owner == sid and nid not in {n.get("id") for n in own}:
            err(where, f"must define the shared node {nid} (notes/file-map.md)")
    for i, e in enumerate(data.get("edges", [])):
        ends = [e.get("from", ""), e.get("to", "")]
        for end in ends:
            if end not in every and not (partial and end in shared):
                err(where, f"edges[{i}]: {end} is not a node")
        if sid not in (ends[0].split("/")[0], ends[1].split("/")[0]):
            err(where, f"edges[{i}]: neither end belongs to {sid}")
    section6 = file_entries(md)
    named = {f for n in own for f in n.get("files", [])}
    for f in section6:
        if not (ROOT / f).exists():
            err(md_where, f"§6 file {f} does not exist")
        if f not in named:
            err(where, f"§6 file {f} is in no node of {sid}")
    for f in primary.get(sid, []):
        if f not in section6:
            err(md_where, f"primary file {f} (notes/file-map.md) has no §6 entry")


def check_index(stage_data: dict[str, dict], every: dict[str, dict], pairs: set) -> None:
    where = "flow/index.json"
    index = load(HERE / "flow" / "index.json")
    if not isinstance(index, dict):
        return err(where, "missing or unreadable")
    check(index, SCHEMA["$defs"]["index_file"], where)
    expected = sorted(f"flow/stages/{sid}.json" for sid in stage_data)
    if sorted(index.get("stage_files", [])) != expected:
        err(where, f"stage_files should be {expected}")
    listed = {s.get("id"): s for s in index.get("stages", []) if isinstance(s, dict)}
    for sid, data in stage_data.items():
        entry = dict(listed.get(sid, {}))
        if not entry:
            err(where, f"stage {sid} is missing from 'stages'")
            continue
        if entry.pop("file", None) != f"flow/stages/{sid}.json":
            err(where, f"stage {sid}: 'file' should be flow/stages/{sid}.json")
        if entry != data.get("stage"):
            err(where, f"stage {sid} differs from the stage node in flow/stages/{sid}.json (copy it again)")
    for i, e in enumerate(index.get("edges", [])):
        if e.get("from") not in listed or e.get("to") not in listed:
            err(where, f"edges[{i}] must join two listed stages")
    links = pairs | {(e.get("from"), e.get("to")) for e in index.get("edges", [])}
    for t in index.get("traces", []):
        steps = t.get("steps", [])
        if steps and t.get("entry") != steps[0]:
            err(where, f"trace {t.get('id')}: 'entry' must be the first step")
        for a, b in zip(steps, steps[1:]):
            if a not in every or b not in every:
                err(where, f"trace {t.get('id')}: {a if a not in every else b} is not a node")
            elif (a, b) not in links:
                err(where, f"trace {t.get('id')}: no edge {a} -> {b}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the walkthrough's flow data against its docs.")
    parser.add_argument("--stage", help="check one stage only, for example s04-scene")
    parser.add_argument("--anchors", metavar="MD", help="print the link anchors of a doc (relative to docs/walkthrough)")
    args = parser.parse_args()
    if args.anchors:
        print("\n".join(anchors((HERE / args.anchors).read_text(encoding="utf-8"))))
        return 0
    primary, shared = file_map()
    stage_data = {}
    for path in sorted((HERE / "flow" / "stages").glob("s[0-9][0-9]-*.json")):
        data = load(path)
        if isinstance(data, dict):
            stage_data[path.stem] = data
    if args.stage and args.stage not in stage_data:
        print(f"flow/stages/{args.stage}.json: missing or unreadable", *errors, sep="\n")
        return 1
    every: dict[str, dict] = {}
    for sid, data in stage_data.items():
        for n in nodes_of(data):
            nid = n.get("id", "?") if isinstance(n, dict) else "?"
            if nid in every and (not args.stage or args.stage in (sid, every[nid].get("stage"))):
                err(f"flow/stages/{sid}.json", f"node id {nid} is defined twice")
            every[nid] = n if isinstance(n, dict) else {}
    pairs = {(e.get("from"), e.get("to")) for d in stage_data.values() for e in d.get("edges", []) if isinstance(e, dict)}
    for sid in [args.stage] if args.stage else stage_data:
        check_stage(sid, stage_data[sid], every, primary, shared, partial=bool(args.stage))
    if not args.stage:
        for sid in primary:
            if sid not in stage_data:
                err(f"flow/stages/{sid}.json", "missing")
        named = {f for n in every.values() for f in n.get("files", [])}
        for md in sorted((HERE / "stages").glob("s[0-9][0-9]-*.md")):
            for cited in sorted(set(CITED_PATH.findall(md.read_text(encoding="utf-8")))):
                if (ROOT / cited).is_file() and cited not in named:
                    err(f"stages/{md.name}", f"cites {cited}, which is in no node")
        check_index(stage_data, every, pairs)
    if errors:
        print(f"{len(errors)} problem(s):", *errors, sep="\n  ")
        return 1
    counts = (len(stage_data) if not args.stage else 1, len(every), len(pairs))
    print("OK" + (f" ({args.stage})" if args.stage else "") + ": %d stage file(s), %d nodes, %d edges known" % counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
