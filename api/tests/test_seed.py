from collections import Counter

from api.seed import load_fixtures, load_participants, load_teams


def test_48_teams_present():
    assert len(load_teams()) == 48


def test_each_participant_has_5_teams():
    for p in load_participants():
        assert len(p.team_ids) == 5, f"{p.id} has {len(p.team_ids)} teams"


def test_no_team_assigned_to_multiple_participants():
    all_ids = [tid for p in load_participants() for tid in p.team_ids]
    assert len(all_ids) == len(set(all_ids))


def test_all_participant_team_ids_exist_in_teams():
    known = {t.id for t in load_teams()}
    for p in load_participants():
        for tid in p.team_ids:
            assert tid in known, f"{tid} (owned by {p.id}) not in teams.json"


def test_all_elo_ratings_positive():
    for t in load_teams():
        assert t.elo_rating > 0, f"{t.id} has non-positive Elo {t.elo_rating}"


def test_load_fixtures_returns_72_matches():
    assert len(load_fixtures()) == 72


def test_fixtures_no_duplicate_ids():
    ids = [f.id for f in load_fixtures()]
    assert len(ids) == len(set(ids))


def test_fixtures_each_team_plays_3_matches():
    appearances: Counter[str] = Counter()
    for f in load_fixtures():
        appearances[f.home_team_id] += 1
        appearances[f.away_team_id] += 1
    bad = {t: n for t, n in appearances.items() if n != 3}
    assert not bad, f"Teams with wrong match count: {bad}"


def test_fixtures_all_group_round():
    for f in load_fixtures():
        assert f.round == "group", f"{f.id} has unexpected round {f.round!r}"
