#!/usr/bin/env python3
"""Generate shared/seed/fixtures.json — WC2026 group-stage fixtures.

All 72 matches sourced from official schedule:
  - 15 matches: TheSportsDB (league 4429, season 2026, API key 123), IDs: tsdb_*
  - 57 matches: Wikipedia WC2026 group-stage pages (June 2026), IDs: wiki_*
  - All kickoff times are UTC.

Run from repo root:
    uv run python scripts/generate_fixtures.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

SEED_DIR = Path(__file__).parent.parent / "shared" / "seed"

# ---------------------------------------------------------------------------
# Complete WC2026 group-stage schedule
# (id, group, matchday, homeTeamId, awayTeamId, scheduledAt, venue, source)
# ---------------------------------------------------------------------------
_SCHEDULE: list[tuple[str, str, int, str, str, str, str, str]] = [
    # --- Group A ---
    ("tsdb_2391728", "A", 1, "MEX", "RSA", "2026-06-11T19:00:00Z", "Estadio Azteca", "thesportsdb"),
    ("tsdb_2461103", "A", 1, "KOR", "CZE", "2026-06-12T02:00:00Z", "Estadio Akron", "thesportsdb"),
    ("wiki_A2_1",    "A", 2, "CZE", "RSA", "2026-06-18T16:00:00Z", "Mercedes-Benz Stadium", "wikipedia"),
    ("wiki_A2_2",    "A", 2, "MEX", "KOR", "2026-06-19T01:00:00Z", "Estadio Akron", "wikipedia"),
    ("wiki_A3_1",    "A", 3, "CZE", "MEX", "2026-06-25T01:00:00Z", "Estadio Azteca", "wikipedia"),
    ("wiki_A3_2",    "A", 3, "RSA", "KOR", "2026-06-25T01:00:00Z", "Estadio BBVA", "wikipedia"),
    # --- Group B ---
    ("tsdb_2461104", "B", 1, "CAN", "BIH", "2026-06-12T19:00:00Z", "BMO Field", "thesportsdb"),
    ("tsdb_2391732", "B", 1, "QAT", "SUI", "2026-06-13T19:00:00Z", "Levi's Stadium", "thesportsdb"),
    ("wiki_B2_1",    "B", 2, "SUI", "BIH", "2026-06-18T19:00:00Z", "SoFi Stadium", "wikipedia"),
    ("wiki_B2_2",    "B", 2, "CAN", "QAT", "2026-06-18T22:00:00Z", "BC Place", "wikipedia"),
    ("wiki_B3_1",    "B", 3, "SUI", "CAN", "2026-06-24T19:00:00Z", "BC Place", "wikipedia"),
    ("wiki_B3_2",    "B", 3, "BIH", "QAT", "2026-06-24T19:00:00Z", "Lumen Field", "wikipedia"),
    # --- Group C ---
    ("tsdb_2391730", "C", 1, "BRA", "MAR", "2026-06-13T22:00:00Z", "MetLife Stadium", "thesportsdb"),
    ("tsdb_2391731", "C", 1, "HAI", "SCO", "2026-06-14T01:00:00Z", "Gillette Stadium", "thesportsdb"),
    ("wiki_C2_1",    "C", 2, "SCO", "MAR", "2026-06-19T22:00:00Z", "Gillette Stadium", "wikipedia"),
    ("wiki_C2_2",    "C", 2, "BRA", "HAI", "2026-06-20T00:30:00Z", "Lincoln Financial Field", "wikipedia"),
    ("wiki_C3_1",    "C", 3, "SCO", "BRA", "2026-06-24T22:00:00Z", "Hard Rock Stadium", "wikipedia"),
    ("wiki_C3_2",    "C", 3, "MAR", "HAI", "2026-06-24T22:00:00Z", "Mercedes-Benz Stadium", "wikipedia"),
    # --- Group D ---
    ("tsdb_2391729", "D", 1, "USA", "PAR", "2026-06-13T01:00:00Z", "SoFi Stadium", "thesportsdb"),
    ("tsdb_2461105", "D", 1, "AUS", "TUR", "2026-06-14T04:00:00Z", "BC Place", "thesportsdb"),
    ("wiki_D2_1",    "D", 2, "USA", "AUS", "2026-06-19T19:00:00Z", "Lumen Field", "wikipedia"),
    ("wiki_D2_2",    "D", 2, "TUR", "PAR", "2026-06-20T03:00:00Z", "Levi's Stadium", "wikipedia"),
    ("wiki_D3_1",    "D", 3, "TUR", "USA", "2026-06-26T02:00:00Z", "SoFi Stadium", "wikipedia"),
    ("wiki_D3_2",    "D", 3, "PAR", "AUS", "2026-06-26T02:00:00Z", "Levi's Stadium", "wikipedia"),
    # --- Group E ---
    ("tsdb_2391733", "E", 1, "GER", "CUW", "2026-06-14T17:00:00Z", "NRG Stadium", "thesportsdb"),
    ("tsdb_2391734", "E", 1, "CIV", "ECU", "2026-06-14T23:00:00Z", "Lincoln Financial Field", "thesportsdb"),
    ("wiki_E2_1",    "E", 2, "GER", "CIV", "2026-06-20T20:00:00Z", "BMO Field", "wikipedia"),
    ("wiki_E2_2",    "E", 2, "ECU", "CUW", "2026-06-21T00:00:00Z", "Arrowhead Stadium", "wikipedia"),
    ("wiki_E3_1",    "E", 3, "CUW", "CIV", "2026-06-25T20:00:00Z", "Lincoln Financial Field", "wikipedia"),
    ("wiki_E3_2",    "E", 3, "ECU", "GER", "2026-06-25T20:00:00Z", "MetLife Stadium", "wikipedia"),
    # --- Group F ---
    ("tsdb_2391735", "F", 1, "NED", "JPN", "2026-06-14T20:00:00Z", "AT&T Stadium", "thesportsdb"),
    ("tsdb_2461106", "F", 1, "SWE", "TUN", "2026-06-15T02:00:00Z", "Estadio BBVA", "thesportsdb"),
    ("wiki_F2_1",    "F", 2, "NED", "SWE", "2026-06-20T17:00:00Z", "NRG Stadium", "wikipedia"),
    ("wiki_F2_2",    "F", 2, "TUN", "JPN", "2026-06-21T04:00:00Z", "Estadio BBVA", "wikipedia"),
    ("wiki_F3_1",    "F", 3, "JPN", "SWE", "2026-06-25T23:00:00Z", "AT&T Stadium", "wikipedia"),
    ("wiki_F3_2",    "F", 3, "TUN", "NED", "2026-06-25T23:00:00Z", "Arrowhead Stadium", "wikipedia"),
    # --- Group G ---
    ("tsdb_2391736", "G", 1, "BEL", "EGY", "2026-06-15T19:00:00Z", "Lumen Field", "thesportsdb"),
    ("wiki_G1_1",    "G", 1, "IRN", "NZL", "2026-06-16T01:00:00Z", "SoFi Stadium", "wikipedia"),
    ("wiki_G2_1",    "G", 2, "BEL", "IRN", "2026-06-21T19:00:00Z", "SoFi Stadium", "wikipedia"),
    ("wiki_G2_2",    "G", 2, "NZL", "EGY", "2026-06-22T01:00:00Z", "BC Place", "wikipedia"),
    ("wiki_G3_1",    "G", 3, "EGY", "IRN", "2026-06-27T03:00:00Z", "Lumen Field", "wikipedia"),
    ("wiki_G3_2",    "G", 3, "NZL", "BEL", "2026-06-27T03:00:00Z", "BC Place", "wikipedia"),
    # --- Group H ---
    ("tsdb_2391739", "H", 1, "ESP", "CPV", "2026-06-15T16:00:00Z", "Mercedes-Benz Stadium", "thesportsdb"),
    ("tsdb_2391738", "H", 1, "KSA", "URU", "2026-06-15T22:00:00Z", "Hard Rock Stadium", "thesportsdb"),
    ("wiki_H2_1",    "H", 2, "ESP", "KSA", "2026-06-21T16:00:00Z", "Mercedes-Benz Stadium", "wikipedia"),
    ("wiki_H2_2",    "H", 2, "URU", "CPV", "2026-06-21T22:00:00Z", "Hard Rock Stadium", "wikipedia"),
    ("wiki_H3_1",    "H", 3, "CPV", "KSA", "2026-06-27T00:00:00Z", "NRG Stadium", "wikipedia"),
    ("wiki_H3_2",    "H", 3, "URU", "ESP", "2026-06-27T00:00:00Z", "Estadio Akron", "wikipedia"),
    # --- Group I ---
    ("wiki_I1_1",    "I", 1, "FRA", "SEN", "2026-06-16T19:00:00Z", "MetLife Stadium", "wikipedia"),
    ("wiki_I1_2",    "I", 1, "IRQ", "NOR", "2026-06-16T22:00:00Z", "Gillette Stadium", "wikipedia"),
    ("wiki_I2_1",    "I", 2, "FRA", "IRQ", "2026-06-22T21:00:00Z", "Lincoln Financial Field", "wikipedia"),
    ("wiki_I2_2",    "I", 2, "NOR", "SEN", "2026-06-23T00:00:00Z", "MetLife Stadium", "wikipedia"),
    ("wiki_I3_1",    "I", 3, "NOR", "FRA", "2026-06-26T19:00:00Z", "Gillette Stadium", "wikipedia"),
    ("wiki_I3_2",    "I", 3, "SEN", "IRQ", "2026-06-26T19:00:00Z", "BMO Field", "wikipedia"),
    # --- Group J ---
    ("wiki_J1_1",    "J", 1, "ARG", "ALG", "2026-06-17T01:00:00Z", "Arrowhead Stadium", "wikipedia"),
    ("wiki_J1_2",    "J", 1, "AUT", "JOR", "2026-06-17T04:00:00Z", "Levi's Stadium", "wikipedia"),
    ("wiki_J2_1",    "J", 2, "ARG", "AUT", "2026-06-22T17:00:00Z", "AT&T Stadium", "wikipedia"),
    ("wiki_J2_2",    "J", 2, "JOR", "ALG", "2026-06-23T03:00:00Z", "Levi's Stadium", "wikipedia"),
    ("wiki_J3_1",    "J", 3, "ALG", "AUT", "2026-06-28T02:00:00Z", "Arrowhead Stadium", "wikipedia"),
    ("wiki_J3_2",    "J", 3, "JOR", "ARG", "2026-06-28T02:00:00Z", "AT&T Stadium", "wikipedia"),
    # --- Group K ---
    ("wiki_K1_1",    "K", 1, "POR", "COD", "2026-06-17T17:00:00Z", "NRG Stadium", "wikipedia"),
    ("wiki_K1_2",    "K", 1, "UZB", "COL", "2026-06-18T02:00:00Z", "Estadio Azteca", "wikipedia"),
    ("wiki_K2_1",    "K", 2, "POR", "UZB", "2026-06-23T17:00:00Z", "NRG Stadium", "wikipedia"),
    ("wiki_K2_2",    "K", 2, "COL", "COD", "2026-06-24T02:00:00Z", "Estadio Akron", "wikipedia"),
    ("wiki_K3_1",    "K", 3, "COL", "POR", "2026-06-27T23:30:00Z", "Hard Rock Stadium", "wikipedia"),
    ("wiki_K3_2",    "K", 3, "COD", "UZB", "2026-06-27T23:30:00Z", "Mercedes-Benz Stadium", "wikipedia"),
    # --- Group L ---
    ("wiki_L1_1",    "L", 1, "ENG", "CRO", "2026-06-17T20:00:00Z", "AT&T Stadium", "wikipedia"),
    ("wiki_L1_2",    "L", 1, "GHA", "PAN", "2026-06-17T23:00:00Z", "BMO Field", "wikipedia"),
    ("wiki_L2_1",    "L", 2, "ENG", "GHA", "2026-06-23T20:00:00Z", "Gillette Stadium", "wikipedia"),
    ("wiki_L2_2",    "L", 2, "PAN", "CRO", "2026-06-23T23:00:00Z", "BMO Field", "wikipedia"),
    ("wiki_L3_1",    "L", 3, "PAN", "ENG", "2026-06-27T21:00:00Z", "MetLife Stadium", "wikipedia"),
    ("wiki_L3_2",    "L", 3, "CRO", "GHA", "2026-06-27T21:00:00Z", "Lincoln Financial Field", "wikipedia"),
]


def main() -> None:
    fixtures: list[dict] = []
    for fid, group, md, home, away, scheduled_at, venue, source in _SCHEDULE:
        fixtures.append(
            {
                "id": fid,
                "type": "match",
                "round": "group",
                "group": group,
                "matchday": md,
                "homeTeamId": home,
                "awayTeamId": away,
                "scheduledAt": scheduled_at,
                "venue": venue,
                "homeScore": None,
                "awayScore": None,
                "winnerId": None,
                "status": "scheduled",
                "source": source,
                "lastUpdated": "2026-06-09T00:00:00Z",
            }
        )

    # Validate: 72 matches, each team plays exactly 3, no duplicate IDs
    assert len(fixtures) == 72, f"Expected 72 fixtures, got {len(fixtures)}"
    ids = [f["id"] for f in fixtures]
    assert len(ids) == len(set(ids)), "Duplicate fixture IDs"
    appearances: Counter[str] = Counter()
    for f in fixtures:
        appearances[f["homeTeamId"]] += 1
        appearances[f["awayTeamId"]] += 1
    bad = {t: n for t, n in appearances.items() if n != 3}
    if bad:
        raise ValueError(f"Teams with wrong match count: {bad}")

    out_path = SEED_DIR / "fixtures.json"
    out_path.write_text(json.dumps(fixtures, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Written {len(fixtures)} fixtures to {out_path}")
    tsdb_count = sum(1 for f in fixtures if f["source"] == "thesportsdb")
    wiki_count = sum(1 for f in fixtures if f["source"] == "wikipedia")
    print(f"  TheSportsDB: {tsdb_count}  Wikipedia: {wiki_count}")


if __name__ == "__main__":
    main()