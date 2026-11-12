"""
Orçamento do Estado (propostas de alteração) tests.

The known values come from the p3 CSVs used by the old streamlit app (../streamlit-votes/p3data),
cross-checked against the source JSON. Those CSVs have three known bugs, so only what they get
right is pinned here: proposta IDs/counts (exact for every year), estados for 2022-2025, and votes
for 2022-2025. The bugs: multi-vote propostas repeat the last vote on every row; dates swap day and
month when the day is <= 12; OE2020/2021 add one blank vote row per proposta.

OE2027 is still in debate when this was written, so nothing about it is pinned.
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app
from etl.transform import TransformError, _as_list, _oe_date, oe_autores, oe_parse_votos

client = TestClient(app)

# --- Parsing (no data needed) -------------------------------------------------------------

SIGLAS = {'partido socialista': 'PS', 'partido social democrata': 'PSD', 'pessoas-animais-natureza': 'PAN'}
DEPUTADOS = {
    'cristina rodrigues': ('Cristina Rodrigues', [('PAN', date(2019, 10, 25), date(2020, 6, 24)),
                                                  ('Ninsc', date(2020, 6, 25), date(2022, 3, 28))]),
    'sara madruga da costa': ('Sara Madruga da Costa', [('PSD', date(2019, 10, 25), None)]),
}


def test_as_list_and_day_first_dates():
    assert _as_list(None) == [] and _as_list({'a': 1}) == [{'a': 1}] and _as_list([1, 2]) == [1, 2]
    assert _oe_date('07/11/2025 20:00:00') == date(2025, 11, 7)


def test_parse_votos_parties_ninsc_and_dissenters():
    votos = [
        {'nome': 'Partido Socialista', 'voto': 'Favor'},
        {'nome': 'Partido Social Democrata', 'voto': 'Contra'},
        {'nome': 'SARA MADRUGA DA COSTA(PSD)', 'voto': 'Abstenção'},
        {'nome': 'CRISTINA RODRIGUES(PAN)', 'voto': 'Ausente'},
    ]
    parsed, named = oe_parse_votos(votos, date(2020, 11, 24), SIGLAS, DEPUTADOS)
    # Non-attached on the vote date: kept with the parties, as in parse_detalhe
    assert parsed == {'a_favor': ['PS'], 'contra': ['PSD'], 'abstencao': [], 'ausencia': ['Cristina Rodrigues (Ninsc)']}
    assert named == [{'nome': 'Sara Madruga da Costa', 'partido': 'PSD', 'sentido': 'abstencao'}]

    # Before leaving PAN she is a named deputy, not Ninsc
    _, named = oe_parse_votos(votos[3:], date(2020, 2, 4), SIGLAS, DEPUTADOS)
    assert named == [{'nome': 'Cristina Rodrigues', 'partido': 'PAN', 'sentido': 'ausencia'}]


def test_parse_votos_rejects_unknown_party_and_vote():
    with pytest.raises(TransformError):
        oe_parse_votos([{'nome': 'Partido Novo', 'voto': 'Favor'}], None, SIGLAS, DEPUTADOS)
    with pytest.raises(TransformError):
        oe_parse_votos([{'nome': 'Partido Socialista', 'voto': 'Talvez'}], None, SIGLAS, DEPUTADOS)


def test_autores_deputies_become_their_party():
    proponentes = [{'nome': 'Cristina Rodrigues', 'partido': 'Ninsc'}]
    autores = ['PS', 'SARA MADRUGA DA COSTA', 'CRISTINA RODRIGUES', 'PS']
    assert oe_autores(autores, proponentes, date(2020, 11, 1), SIGLAS, DEPUTADOS) == ['PS', 'PSD']
    with pytest.raises(TransformError):
        oe_autores(['NINGUÉM CONHECIDO'], [], None, SIGLAS, DEPUTADOS)


# --- Known values ----------------------------------------------------------------------------

# ano: (propostas, votacoes); propostas match the p3 CSVs exactly, votes are the source JSON's
KNOWN = {
    2020: (1333, 1451), 2021: (1547, 1652), 2022: (1505, 1553), 2023: (1862, 1961),
    2024: (1938, 2013), 2025: (2162, 2162), 2026: (2193, 2253),
}
# Approved propostas, equal to the p3 CSVs (later years had source corrections after the snapshot)
APROVADAS = {2022: 141, 2023: 146, 2024: 206, 2025: 248}


@pytest.fixture(scope="module")
def orcamentos():
    body = client.get("/api/v1/oe/").json()
    return {o["ano"]: o for o in body["data"]}


@pytest.mark.parametrize("ano", KNOWN)
def test_known_counts(orcamentos, ano):
    assert (orcamentos[ano]["propostas"], orcamentos[ano]["votacoes"]) == KNOWN[ano]
    if ano in APROVADAS:
        assert orcamentos[ano]["aprovadas"] == APROVADAS[ano]


def test_votes_count_matches_list_endpoint(orcamentos):
    total = client.get("/api/v1/oe/votacoes/?ano=2024&limit=1").json()["pagination"]["total"]
    assert total == orcamentos[2024]["votacoes"]


def test_dates_are_day_first():
    """OE2024 propostas were all submitted in November 2023 (the p3 CSVs spread them over the year)."""
    body = client.get("/api/v1/oe/propostas/?ano=2024&limit=1").json()
    total = body["pagination"]["total"]
    november = client.get("/api/v1/oe/propostas/?ano=2024&data_desde=2023-11-01&data_ate=2023-11-30&limit=1").json()
    assert november["pagination"]["total"] == total


def test_known_vote():
    """2076C (OE2026, L): approved in committee, 21/11/2025."""
    vote = client.get("/api/v1/oe/votacoes/25333_1").json()
    assert vote["numero"] == "2076C" and vote["data"] == "2025-11-21" and vote["tipo_reuniao"] == "COM"
    assert vote["autores_gp"] == ["L"] and vote["resultado"] == "Aprovado(a)"
    assert vote["detalhe_parsed"] == {
        "a_favor": ["CH", "IL", "L", "PCP", "BE", "PAN"], "contra": [], "abstencao": ["PSD", "PS", "CDS-PP"], "ausencia": [],
    }


def test_ninsc_and_regional_deputies():
    """OE2021: Cristina Rodrigues votes as Ninsc; PSD Madeira deputies vote apart from PSD."""
    ninsc = client.get("/api/v1/oe/votacoes/13218_1").json()  # 71C, 23/11/2020
    assert ninsc["detalhe_parsed"]["a_favor"][-1] == "Joacine Katar Moreira (Ninsc)"
    assert ninsc["detalhe_parsed"]["abstencao"] == ["PSD", "CDS-PP", "Cristina Rodrigues (Ninsc)"]
    assert ninsc["detalhe_deputados"] == []

    dissent = client.get("/api/v1/oe/votacoes/13298_1").json()  # 151C, 20/11/2020
    assert "PSD" in dissent["detalhe_parsed"]["abstencao"]
    assert dissent["detalhe_deputados"] == [{"nome": "Sara Madruga da Costa", "partido": "PSD", "sentido": "a_favor"}]


# --- Filters ---------------------------------------------------------------------------------

def test_proposta_filters():
    body = client.get("/api/v1/oe/propostas/?ano=2026&autor_gp=cds-pp&estado=aprovado&limit=500").json()
    assert body["pagination"]["total"] > 0
    assert all("CDS-PP" in p["autores_gp"] and p["estado"].startswith("Aprovad") for p in body["data"])

    proposta = client.get("/api/v1/oe/propostas/25333").json()
    assert proposta["numero"] == "2076C" and proposta["n_votacoes"] == 1
    assert {pr["partido"] for pr in proposta["proponentes"]} == {"L"}


def test_vote_filters():
    body = client.get("/api/v1/oe/votacoes/?ano=2026&partido_favor=L&tipo_reuniao=rp&limit=500").json()
    assert body["pagination"]["total"] > 0
    assert all("L" in v["detalhe_parsed"]["a_favor"] and v["tipo_reuniao"] == "RP" for v in body["data"])


def test_budget_in_debate_has_valid_empty_or_full_votes():
    """The current budget may have no votes yet: the endpoint must still work."""
    current = max(o["ano"] for o in client.get("/api/v1/oe/").json()["data"])
    assert client.get(f"/api/v1/oe/votacoes/?ano={current}").status_code == 200
    assert client.get(f"/api/v1/oe/propostas/?ano={current}").json()["pagination"]["total"] > 0


def test_party_codes_with_one_letter_or_hyphen_accepted():
    """REGRESSION: the party validator rejected L and CDS-PP (400) on every endpoint."""
    for code in ("L", "cds-pp"):
        assert client.get(f"/api/v1/iniciativas/votacoes/?partido_favor={code}&limit=1").status_code == 200
    assert client.get("/api/v1/iniciativas/votacoes/?partido_favor=P$D&limit=1").status_code == 400
