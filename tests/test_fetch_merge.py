"""
merge_iniciativas: upstream wins, dropped records are carried forward, lost votes are refused.
Added fue to intermittent failures of the API, sometimes it drops sessions while the rest if OK.
"""

import json

import pytest

from etl.fetch import FetchError, merge_iniciativas


def ini(ini_id, *vote_ids, titulo="t"):
    return {"IniId": ini_id, "IniTitulo": titulo,
            "IniEventos": [{"Votacao": [{"id": v} for v in vote_ids]}]}


def test_upstream_wins_and_dropped_records_carried():
    old = [ini(1, "v1", titulo="old"), ini(2, "v2")]
    new = [ini(1, "v1", "v3", titulo="new"), ini(3)]
    merged, carried = merge_iniciativas(old, new)
    by_id = {x["IniId"]: x for x in merged}
    assert carried == 1
    assert set(by_id) == {1, 2, 3}
    assert by_id[1]["IniTitulo"] == "new"


def test_lost_vote_in_present_record_is_refused():
    old = [ini(1, "v1", "v2")]
    new = [ini(1, "v1")]
    with pytest.raises(FetchError, match="lose 1 votes"):
        merge_iniciativas(old, new)


def test_committee_votes_count():
    old = [{"IniId": 1, "IniEventos": [{"Comissao": [{"Votacao": [{"id": "c1"}]}]}]}]
    with pytest.raises(FetchError):
        merge_iniciativas(old, [{"IniId": 1, "IniEventos": []}])


def test_shrink_check(tmp_path):
    from etl.fetch import check_shrink
    old = tmp_path / "atividades.json"
    old.write_text(json.dumps({"Debates": [{"id": i} for i in range(20)], "AtividadesGerais": {"Atividades": [{"id": 1}]}}))
    check_shrink(old, {"Debates": [{"id": i} for i in range(19)], "AtividadesGerais": {"Atividades": [{"id": 1}]}})  # -5% passes
    with pytest.raises(FetchError, match="Debates"):  # one all-null placeholder counts as empty
        check_shrink(old, {"Debates": [{"id": None}], "AtividadesGerais": {"Atividades": [{"id": 1}]}})
    with pytest.raises(FetchError, match="AtividadesGerais.Atividades"):
        check_shrink(old, {"Debates": [{"id": i} for i in range(20)], "AtividadesGerais": {"Atividades": []}})
