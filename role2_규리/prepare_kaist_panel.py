"""Convert the version-1 KAIST public sleep diary into the existing daily replay format.

Baigutanova et al., figshare (CC BY 4.0), DOI 10.6084/m9.figshare.28509740.v1.
The study provides three clock fields. Its published time in bed equals wake time
minus bedtime, so the replay uses wake time as the end of the bed interval.
"""

import argparse
import csv
from datetime import date, time
import hashlib
from pathlib import Path


SOURCE_MD5 = "acf1709cc04c32f323932d5e0839c931"


def clock(value):
    stamp = time.fromisoformat(value)
    if stamp.second or stamp.microsecond:
        raise ValueError("the replay expects minute-resolution clocks")
    seconds = (stamp.hour * 60 + stamp.minute) * 60
    return seconds, "AM" if stamp.hour < 12 else "PM"


def prepare(source, target):
    if hashlib.md5(source.read_bytes()).hexdigest() != SOURCE_MD5:
        raise ValueError("input checksum differs from figshare version 1 sleep_diary.csv")
    with source.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    starts = {}
    for row in rows:
        pid = row["userId"]
        day = date.fromisoformat(row["date"])
        starts[pid] = min(starts.get(pid, day), day)
    output = []
    missing_waso = 0
    for row in rows:
        bed, asleep, wake = (clock(row[key]) for key in ("go2bed", "asleep", "wakeup"))
        duration = (wake[0] - bed[0]) % 86400 / 3600
        if abs(duration - float(row["in_bed_duration"])) > 1e-6:
            raise ValueError("published time in bed disagrees with the three-clock mapping")
        if not row["waso"].strip():
            missing_waso += 1
            continue
        waso = float(row["waso"])
        if not waso.is_integer() or waso < 0:
            raise ValueError("WASO should be a nonnegative count of minutes")
        h, m = divmod(int(waso), 60)
        pid = row["userId"]
        day = (date.fromisoformat(row["date"]) - starts[pid]).days
        clocks = []
        for seconds, ampm in (bed, asleep, wake, wake):
            hour, rem = divmod(seconds, 3600)
            clocks.extend(((hour % 12 or 12) * 3600 + rem, ampm))
        output.append((pid, day, *clocks, f"{h:02d}:{m:02d}"))
    if len(set((row[0], row[1]) for row in output)) != len(output):
        raise ValueError("duplicate participant-day")
    with target.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("pid", "day_num", "tb", "tb_ap", "ts", "ts_ap", "ta", "ta_ap",
                         "tg", "tg_ap", "waso_est"))
        writer.writerows(output)
    print(f"{len(rows)} input nights, {len(starts)} participants, {missing_waso} missing WASO, "
          f"{len(output)} nights exported")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path, help="new daily CSV outside the repository")
    args = parser.parse_args()
    prepare(args.source, args.target)
