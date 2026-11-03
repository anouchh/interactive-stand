"""Проверка комплектации и анализ журнала одного сеанса принятой версии."""
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


def main():
    root = Path(__file__).resolve().parent / "example"
    data = json.loads((root / "case.json").read_text(encoding="utf-8"))
    for version in data["versions"]:
        index, errors = inspect_package(root, version["items"])
        print(version["id"], "errors", errors)
        if not errors:
            counts, rejected = summarize(index, data["events"])
            print("counts", counts, "rejected", rejected)


if __name__ == "__main__":
    main()
