"""Проверка комплектации и анализ журнала одного сеанса принятой версии."""
import csv
import hashlib
import json
from pathlib import Path


def inspect_package(root, items):
    """Имена ресурсов — простые имена файлов в каталоге пакета."""
    index = {}
    errors = []
    if not items:
        errors.append("empty_catalog")
    for zone, filename, expected in items:
        if not zone or zone in index:
            errors.append(f"invalid_zone:{zone}")
        index[zone] = filename
        if not filename or Path(filename).name != filename:
            errors.append(f"invalid_name:{zone}")
            continue
        try:
            digest = hashlib.sha256((root / filename).read_bytes()).hexdigest()
        except OSError:
            errors.append(f"unreadable:{zone}")
            continue
        if digest != expected:
            errors.append(f"checksum:{zone}")
    return ({} if errors else index), errors


def summarize(index, events, interval=250):
    """Один сеанс, один сенсор, целое время от начала сеанса в мс."""
    last = {}
    counts = dict.fromkeys(index, 0)
    rejected = []
    previous = -1
    for number, (at, zone) in enumerate(events, 1):
        if type(at) is not int or at < 0 or at < previous:
            rejected.append([number, "time"])
            continue
        previous = at
        if zone not in index:
            rejected.append([number, "unknown"])
        elif zone in last and at - last[zone] < interval:
            rejected.append([number, "repeat"])
        else:
            last[zone] = at
            counts[zone] += 1
    return counts, rejected


def admitted_sessions(root, data):
    packages = {}
    for version in data["versions"]:
        index, errors = inspect_package(root, version["items"])
        print(version["id"], "errors", errors)
        if version["id"] in packages:
            raise ValueError("duplicate_version")
        packages[version["id"]] = index
    decisions = {row["protocol"]: row for row in data["decisions"]}
    if len(decisions) != len(data["decisions"]):
        raise ValueError("duplicate_protocol")
    sessions = {}
    for session in data["sessions"]:
        decision = decisions[session["protocol"]]
        version = decision["version"]
        if decision["result"] != "accepted" or not packages[version]:
            raise ValueError("not_admitted")
        if session["id"] in sessions:
            raise ValueError("duplicate_session")
        sessions[session["id"]] = (version, packages[version])
    return sessions


def read_events(stream):
    fields = ["session", "version", "time_ms", "zone"]
    if next(stream, "").rstrip("\r\n").split("\t") != fields:
        raise ValueError("header")
    for line_number, line in enumerate(stream, 2):
        values = line.rstrip("\r\n").split("\t")
        if len(values) != len(fields):
            raise ValueError(f"line {line_number}: expected {len(fields)} columns, got {len(values)}")
        yield dict(zip(fields, values))


def analyze_log(sessions, session_id, rows):
    version, index = sessions[session_id]
    events = []
    for row in rows:
        if row["session"] != session_id or row["version"] != version:
            raise ValueError("binding")
        value = row["time_ms"]
        at = int(value) if value.isascii() and value.isdecimal() else None
        events.append((at, row["zone"]))
    return summarize(index, events)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", type=Path)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--session", default="S1")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent / "example"
    data = json.loads((root / "case.json").read_text(encoding="utf-8"))
    sessions = admitted_sessions(root, data)
    with (args.log or root / "events.tsv").open(encoding="utf-8", newline="") as stream:
        counts, rejected = analyze_log(sessions, args.session, read_events(stream))
    print("counts", counts, "rejected", rejected)
    if args.export:
        with args.export.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
            writer.writerow(["session", "version", "zone"])
            for key, (version, index) in sessions.items():
                writer.writerows((key, version, zone) for zone in index)


if __name__ == "__main__":
    main()
