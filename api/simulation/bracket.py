"""WC2026 tournament bracket structure.

WC2026 format:
  - 48 teams, 12 groups (A–L) of 4 teams each
  - Group stage: 3 matchdays, 6 matches per group (72 total)
  - Advancement: top 2 from each group + 8 best 3rd-place teams = 32 teams
  - Knockout: R32 (16 matches) → R16 (8) → QF (4) → SF (2) → Final (1)

R32 bracket slots
-----------------
FIFA defined 8 "pods" for R32. Each pod is a mini-bracket of 4 teams that feeds
into a shared quarter of the draw. Pods are indexed 1–8, each containing exactly
2 R32 matches whose winners meet in R16.

Real WC2026 R32 structure (FIFA official bracket):
  - 4 matches: group winner vs group runner-up
  - 8 matches: group winner vs best 3rd-place team
  - 4 matches: group runner-up vs group runner-up

Slot | FIFA match | Home slot         | Away slot
-----|------------|-------------------|------------------
 1   |    73      | Runner-up Group A | Runner-up Group B
 2   |    74      | Winner Group E    | Best 3rd (A/B/C/D/F)
 3   |    75      | Winner Group F    | Runner-up Group C
 4   |    76      | Winner Group C    | Runner-up Group F
 5   |    77      | Winner Group I    | Best 3rd (C/D/F/G/H)
 6   |    78      | Runner-up Group E | Runner-up Group I
 7   |    79      | Winner Group A    | Best 3rd (C/E/F/H/I)
 8   |    80      | Winner Group L    | Best 3rd (E/H/I/J/K)
 9   |    81      | Winner Group D    | Best 3rd (B/E/F/I/J)
10   |    82      | Winner Group G    | Best 3rd (A/E/H/I/J)
11   |    83      | Runner-up Group K | Runner-up Group L
12   |    84      | Winner Group H    | Runner-up Group J
13   |    85      | Winner Group B    | Best 3rd (E/F/G/I/J)
14   |    86      | Winner Group J    | Runner-up Group H
15   |    87      | Winner Group K    | Best 3rd (D/E/I/J/L)
16   |    88      | Runner-up Group D | Runner-up Group G

Slots with "Best 3rd": a 3rd-place qualifier assigned at runtime by ranking
the 8 best 3rd-place teams (best→worst) and distributing them sequentially
across the 8 available slots. The exact FIFA seeding table (495 group-combination
rows) is approximated by this sequential assignment.

R16 bracket links adjacent R32 slot winners (pod pairs):
  R16-1: winner(slot 1) vs winner(slot 2)   [m73 vs m74]
  R16-2: winner(slot 3) vs winner(slot 4)   [m75 vs m76]
  R16-3: winner(slot 5) vs winner(slot 6)   [m77 vs m78]
  R16-4: winner(slot 7) vs winner(slot 8)   [m79 vs m80]
  R16-5: winner(slot 9) vs winner(slot 10)  [m81 vs m82]
  R16-6: winner(slot 11) vs winner(slot 12) [m83 vs m84]
  R16-7: winner(slot 13) vs winner(slot 14) [m85 vs m86]
  R16-8: winner(slot 15) vs winner(slot 16) [m87 vs m88]

QF / SF / Final follow standard single-elimination.
"""

from __future__ import annotations

from typing import Literal

# Slot descriptor type.
# group is None for 3rd-place slots (resolved at runtime from ranked pool).
_Pos = Literal["1st", "2nd", "3rd"]

# ---------------------------------------------------------------------------
# Group round-robin matchday structure
# ---------------------------------------------------------------------------

GROUPS: list[str] = list("ABCDEFGHIJKL")

# Matchday 3 is the simultaneous final matchday; both group matches kick off
# at the same time. The simulation engine must process these as one atomic step.
FINAL_MATCHDAY = 3


# ---------------------------------------------------------------------------
# R32 slot definitions; official FIFA WC2026 bracket
#
# Each entry is (home_desc, away_desc) where desc = (group | None, position).
# group=None means "best 3rd-place team", resolved sequentially from the
# ranked pool in the simulation engine (best 3rd-place → first None slot).
# ---------------------------------------------------------------------------

R32_SLOTS: list[tuple[tuple[str | None, _Pos], tuple[str | None, _Pos]]] = [
    # slot 1 ; m73
    (("A", "2nd"), ("B", "2nd")),
    # slot 2 ; m74
    (("E", "1st"), (None, "3rd")),
    # slot 3 ; m75
    (("F", "1st"), ("C", "2nd")),
    # slot 4 ; m76
    (("C", "1st"), ("F", "2nd")),
    # slot 5 ; m77
    (("I", "1st"), (None, "3rd")),
    # slot 6 ; m78
    (("E", "2nd"), ("I", "2nd")),
    # slot 7 ; m79
    (("A", "1st"), (None, "3rd")),
    # slot 8 ; m80
    (("L", "1st"), (None, "3rd")),
    # slot 9 ; m81
    (("D", "1st"), (None, "3rd")),
    # slot 10; m82
    (("G", "1st"), (None, "3rd")),
    # slot 11; m83
    (("K", "2nd"), ("L", "2nd")),
    # slot 12; m84
    (("H", "1st"), ("J", "2nd")),
    # slot 13; m85
    (("B", "1st"), (None, "3rd")),
    # slot 14; m86
    (("J", "1st"), ("H", "2nd")),
    # slot 15; m87
    (("K", "1st"), (None, "3rd")),
    # slot 16; m88
    (("D", "2nd"), ("G", "2nd")),
]

# ---------------------------------------------------------------------------
# R16 bracket: pairs of R32 slot indices (1-based) whose winners meet in R16
# ---------------------------------------------------------------------------

R16_BRACKET: list[tuple[int, int]] = [
    (1, 3),  # r16_90: r32_73 vs r32_75  (NRG Stadium, Houston, Jul 4)
    (2, 5),  # r16_89: r32_74 vs r32_77  (Philadelphia, Jul 4)
    (4, 6),  # r16_91: r32_76 vs r32_78  (MetLife, Jul 5)
    (7, 8),  # r16_92: r32_79 vs r32_80  (Azteca, Jul 5)
    (9, 10),  # r16_94: r32_81 vs r32_82  (Seattle, Jul 6)
    (11, 12),  # r16_93: r32_83 vs r32_84  (Dallas, Jul 6)
    (13, 15),  # r16_96: r32_85 vs r32_87  (Vancouver, Jul 7)
    (14, 16),  # r16_95: r32_86 vs r32_88  (Atlanta, Jul 7)
]

# QF: pairs of R16 match indices (1-based)
QF_BRACKET: list[tuple[int, int]] = [
    (2, 1),  # qf_97: r16_89 winner vs r16_90 winner (Foxborough, Jul 9)
    (6, 5),  # qf_98: r16_93 winner vs r16_94 winner (SoFi, Jul 10)
    (3, 4),  # qf_99: r16_91 winner vs r16_92 winner (Miami, Jul 11)
    (8, 7),  # qf_100: r16_95 winner vs r16_96 winner (KC, Jul 11)
]

# SF: pairs of QF match indices (1-based)
SF_BRACKET: list[tuple[int, int]] = [
    (1, 2),  # SF-1
    (3, 4),  # SF-2
]

# ---------------------------------------------------------------------------
# Elo win-probability formula (neutral site, no home-field adjustment)
# ---------------------------------------------------------------------------

ELO_DIVISOR = 400.0


def elo_win_prob(elo_a: float, elo_b: float) -> float:
    """Return probability that team A beats team B."""
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / ELO_DIVISOR))


# ---------------------------------------------------------------------------
# Group-stage tiebreaker order (for determining 1st/2nd/3rd within a group)
# ---------------------------------------------------------------------------
# FIFA WC2026 group-stage tiebreaker criteria (in order):
#   1. Points (win=3, draw=1, loss=0)
#   2. Goal difference (GD)
#   3. Goals for (GF)
#   4. Head-to-head points
#   5. Head-to-head GD
#   6. Drawing of lots (not modelled in simulation; use random tiebreak)

TIEBREAK_CRITERIA = ["points", "gd", "gf", "h2h_points", "h2h_gd", "random"]
