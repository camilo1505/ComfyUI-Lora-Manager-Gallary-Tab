#!/usr/bin/env python3
"""Git merge driver for locale JSON files.

Performs a deep, key-level three-way merge of translation files so that two
branches adding different keys to the same locale do not produce content
conflicts. The branch being merged in (theirs / %B) wins on shared keys that
both sides changed differently, while keys unique to either side are always
kept.

Configure in a repo that has this driver declared via ``.gitattributes``::

    git config merge.locales.driver "python3 scripts/merge_locales_driver.py %O %A %B"

Git invokes the driver with three paths:
  %O  ancestor (merge base) version
  %A  current branch (ours) version -- the merged result is written back here
  %B  other branch (theirs) version being merged in
Exit code 0 signals a clean auto-merge; non-zero leaves the file conflicted.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CANONICAL_INDENT = 4
CANONICAL_SEPARATORS = (",", ": ")


def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def _is_leaf(value) -> bool:
    return not isinstance(value, dict)


def _deep_merge(base: dict, ours: dict, theirs: dict) -> dict:
    """Merge two dicts at key level.

    - Keys present in both are merged recursively (dicts) or compared as
      leaves. A shared leaf changed differently on both sides resolves in
      favor of ``theirs`` (the branch being merged in).
    - Keys unique to either side are always kept.
    """
    result: dict = {}
    ordered_keys = list(theirs.keys()) + [k for k in ours.keys() if k not in theirs]

    for key in ordered_keys:
        if key in ours and key in theirs:
            our_value = ours[key]
            their_value = theirs[key]
            if isinstance(our_value, dict) and isinstance(their_value, dict):
                base_value = base.get(key) if isinstance(base.get(key), dict) else {}
                result[key] = _deep_merge(base_value, our_value, their_value)
            elif our_value == their_value:
                result[key] = our_value
            elif isinstance(base, dict) and base.get(key) == their_value:
                # Only ours changed this leaf -> keep ours.
                result[key] = our_value
            elif isinstance(base, dict) and base.get(key) == our_value:
                # Only theirs changed this leaf -> take theirs.
                result[key] = their_value
            else:
                # Both changed it differently -> prefer the merged-in branch.
                result[key] = their_value
        elif key in ours:
            result[key] = ours[key]
        else:
            result[key] = theirs[key]

    return result


def _canonical(data: dict) -> str:
    return json.dumps(data, indent=CANONICAL_INDENT, ensure_ascii=False,
                      separators=CANONICAL_SEPARATORS) + "\n"


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: merge_locales_driver.py <ancestor> <ours> <theirs>", file=sys.stderr)
        return 1

    base_path, ours_path, theirs_path = sys.argv[1], sys.argv[2], sys.argv[3]

    try:
        base = _load(base_path)
        ours = _load(ours_path)
        theirs = _load(theirs_path)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"merge_locales_driver: cannot parse a locale file: {exc}", file=sys.stderr)
        return 1

    merged = _deep_merge(base, ours, theirs)
    Path(ours_path).write_text(_canonical(merged), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())