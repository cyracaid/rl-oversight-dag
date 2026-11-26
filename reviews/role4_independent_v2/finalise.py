"""Re-aggregate summary.csv from raw rows.csv (aggregation-only change)."""
import sys

from runner import COLUMNS, load_rows, summarise, write_csv

for block in sys.argv[1:]:
    rows = summarise(load_rows(f"{block}/rows.csv"))
    write_csv(f"{block}/summary.csv", rows, COLUMNS, fmt=True)
    print(block, len(rows), "rows written")
