import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SRG = ROOT / "tools/mappings/srg/joined.srg"
STABLE = ROOT / "tools/mappings/stable39"

OUTPUT = ROOT / "research/mapping_index.json"

classes = {}
fields = {}
methods = {}

def load_csv(filename):
    path = STABLE / filename
    with path.open("r", encoding="utf-8", newline="") as f:
        return {
            row["searge"]: row["name"]
            for row in csv.DictReader(f)
        }

stable_fields = load_csv("fields.csv")
stable_methods = load_csv("methods.csv")

with SRG.open("r", encoding="utf-8") as f:
    for line in f:
        parts = line.strip().split()

        if not parts:
            continue

        kind = parts[0]

        if kind == "CL:" and len(parts) == 3:
            classes[parts[1]] = parts[2]

        elif kind == "FD:" and len(parts) == 3:
            obf_owner, obf_name = parts[1].rsplit("/", 1)
            srg_owner, srg_name = parts[2].rsplit("/", 1)

            key = f"{obf_owner}/{obf_name}"

            fields[key] = {
                "owner": srg_owner,
                "srg": srg_name,
                "name": stable_fields.get(srg_name, srg_name),
            }

        elif kind == "MD:" and len(parts) == 5:
            obf_owner, obf_name = parts[1].rsplit("/", 1)
            srg_owner, srg_name = parts[3].rsplit("/", 1)

            key = f"{obf_owner}/{obf_name} {parts[2]}"

            methods[key] = {
                "owner": srg_owner,
                "srg": srg_name,
                "name": stable_methods.get(srg_name, srg_name),
                "obfuscated_descriptor": parts[2],
                "srg_descriptor": parts[4],
            }

result = {
    "minecraft_version": "1.12.2",
    "mapping_version": "MCP Stable 39",
    "classes": classes,
    "fields": fields,
    "methods": methods,
}

OUTPUT.write_text(
    json.dumps(result, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print("Mapping index created!")
print("Classes:", len(classes))
print("Fields:", len(fields))
print("Methods:", len(methods))
print("Output:", OUTPUT)
