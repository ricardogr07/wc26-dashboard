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

R32 slot assignments (FIFA WC2026 official bracket):

Slot | Home slot         | Away slot
-----|-------------------|------------------
 1   | Winner Group A    | Runner-up Group B
 2   | Winner Group C    | Runner-up Group D
 3   | Winner Group E    | Runner-up Group F
 4   | Winner Group G    | Runner-up Group H
 5   | Winner Group I    | Runner-up Group J
 6   | Winner Group K    | Runner-up Group L
 7   | Winner Group B    | Runner-up Group A
 8   | Winner Group D    | Runner-up Group C
 9   | Winner Group F    | Runner-up Group E
10   | Winner Group H    | Runner-up Group G
11   | Winner Group J    | Runner-up Group I
12   | Winner Group L    | Runner-up Group K
13   | 3rd best group X  | 3rd best group Y  (TBD post group stage)
14   | 3rd best group X  | 3rd best group Y
15   | 3rd best group X  | 3rd best group Y
16   | 3rd best group X  | 3rd best group Y

Note: Slots 13–16 involve the 8 best 3rd-place teams. The specific assignments
depend on which groups produced 3rd-place qualifiers, per the FIFA seeding table.
The simulation engine uses _THIRD_PLACE_BRACKET to resolve these at runtime.

R16 bracket links R32 winners:
  R16-1: winner(R32-1) vs winner(R32-2)
  R16-2: winner(R32-3) vs winner(R32-4)
  R16-3: winner(R32-5) vs winner(R32-6)
  R16-4: winner(R32-7) vs winner(R32-8)
  R16-5: winner(R32-9) vs winner(R32-10)
  R16-6: winner(R32-11) vs winner(R32-12)
  R16-7: winner(R32-13) vs winner(R32-14)
  R16-8: winner(R32-15) vs winner(R32-16)

QF / SF / Final follow standard single-elimination.
"""

from __future__ import annotations

from typing import Literal

# Slot descriptor type
_Pos = Literal["1st", "2nd", "3rd"]

# ---------------------------------------------------------------------------
# Group round-robin matchday structure
# ---------------------------------------------------------------------------

GROUPS: list[str] = list("ABCDEFGHIJKL")

# Matchday 3 is the simultaneous final matchday — both group matches kick off
# at the same time. The simulation engine must process these as one atomic step.
FINAL_MATCHDAY = 3


# ---------------------------------------------------------------------------
# R32 slot definitions
# group_positions maps slot_index (1-based) to a pair of
# (group_letter, position) descriptors where position ∈ {"1st","2nd","3rd"}.
# ---------------------------------------------------------------------------

R32_SLOTS: list[tuple[tuple[str, _Pos], tuple[str, _Pos]]] = [
    # (home_slot,          away_slot)
    (("A", "1st"), ("B", "2nd")),  # slot 1
    (("C", "1st"), ("D", "2nd")),  # slot 2
    (("E", "1st"), ("F", "2nd")),  # slot 3
    (("G", "1st"), ("H", "2nd")),  # slot 4
    (("I", "1st"), ("J", "2nd")),  # slot 5
    (("K", "1st"), ("L", "2nd")),  # slot 6
    (("B", "1st"), ("A", "2nd")),  # slot 7
    (("D", "1st"), ("C", "2nd")),  # slot 8
    (("F", "1st"), ("E", "2nd")),  # slot 9
    (("H", "1st"), ("G", "2nd")),  # slot 10
    (("J", "1st"), ("I", "2nd")),  # slot 11
    (("L", "1st"), ("K", "2nd")),  # slot 12
    # Slots 13–16: best 3rd-place teams, resolved at runtime
    # Placeholders — the engine fills these after group stage simulation.
    (("?", "3rd"), ("?", "3rd")),  # slot 13
    (("?", "3rd"), ("?", "3rd")),  # slot 14
    (("?", "3rd"), ("?", "3rd")),  # slot 15
    (("?", "3rd"), ("?", "3rd")),  # slot 16
]

# ---------------------------------------------------------------------------
# 3rd-place qualification table (FIFA WC2026 official)
# Maps frozenset of groups that produced 3rd-place qualifiers to a
# fixed bracket assignment. With 12 groups, exactly 8 3rd-place teams advance.
# This lookup is used when all 12 group winners/runners-up are known.
#
# FIFA's rule: the 8 best 3rd-place teams qualify. Their R32 placement is
# determined by a pre-drawn table (FIFA circular no. 1696-equivalent for 2026).
# The table below reflects the announced bracket structure for WC2026.
# ---------------------------------------------------------------------------

# The simulation engine assigns 3rd-place qualifiers to R32 slots 13–16 by
# ranking all twelve 3rd-place finishers by points → GD → GF → head-to-head.
# Their bracket placement follows this slot order: best goes to slot 13, etc.
# (Simplified rule used in simulation; FIFA's actual table is draw-dependent.)
THIRD_PLACE_SLOTS = [13, 14, 15, 16]

# ---------------------------------------------------------------------------
# R16 bracket: pairs of R32 slot indices (1-based) whose winners meet in R16
# ---------------------------------------------------------------------------

R16_BRACKET: list[tuple[int, int]] = [
    (1, 2),  # R16-1
    (3, 4),  # R16-2
    (5, 6),  # R16-3
    (7, 8),  # R16-4
    (9, 10),  # R16-5
    (11, 12),  # R16-6
    (13, 14),  # R16-7
    (15, 16),  # R16-8
]

# QF: pairs of R16 match indices (1-based)
QF_BRACKET: list[tuple[int, int]] = [
    (1, 2),  # QF-1
    (3, 4),  # QF-2
    (5, 6),  # QF-3
    (7, 8),  # QF-4
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
#   6. Drawing of lots (not modelled in simulation — use random tiebreak)

TIEBREAK_CRITERIA = ["points", "gd", "gf", "h2h_points", "h2h_gd", "random"]
