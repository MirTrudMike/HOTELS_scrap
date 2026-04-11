#!/usr/bin/env python3
"""One-time migration script: converts base JSON files from flat format to history format.

Old format:
    {"id": "...", "name": "Hotel ABC", "stars": 4, "date_parsed": "15.03.2024", ...}

New format:
    {"id": "...", "date_parsed": "15.03.2024", "name": {"15.03.2024": "Hotel ABC"}, "stars": {"15.03.2024": 4}, ...}

Run once from the project root:
    python scripts/migrate_base.py

Safe to run repeatedly — already-migrated files are skipped.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
BASE_DIR = PROJECT_ROOT / 'base'

TRACKED_FIELDS = (
    'name', 'stars', 'rating', 'number_of_reviews',
    'district', 'city', 'new_mark', 'link', 'foto',
)


def _is_old_format(record: dict) -> bool:
    """Return True if the record uses the old flat format (name is a string, not a dict)."""
    name_val = record.get('name')
    return name_val is None or not isinstance(name_val, dict)


def migrate_record(record: dict) -> dict:
    """Convert a single flat record to the history format."""
    date = record.get('date_parsed', '01.01.2000')
    new_record = {
        'id': record['id'],
        'date_parsed': date,
    }
    for field in TRACKED_FIELDS:
        value = record.get(field)
        new_record[field] = {date: value}
    return new_record


def migrate_file(path: Path) -> None:
    print(f"Processing: {path.name} ...", end=' ')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    if not data:
        print("empty, skipped.")
        return

    if not _is_old_format(data[0]):
        print("already migrated, skipped.")
        return

    migrated = [migrate_record(r) for r in data]

    backup_path = path.with_suffix('.json.bak')
    path.rename(backup_path)
    print(f"backup saved to {backup_path.name}", end=' ... ')

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(migrated, f, indent=4, ensure_ascii=False)

    print(f"done. Migrated {len(migrated)} records.")


def main():
    json_files = sorted(BASE_DIR.glob('*.json'))
    if not json_files:
        print(f"No JSON files found in {BASE_DIR}")
        sys.exit(0)

    print(f"Found {len(json_files)} file(s) in {BASE_DIR}\n")
    for path in json_files:
        migrate_file(path)
    print("\nMigration complete.")


if __name__ == '__main__':
    main()
