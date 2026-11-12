"""
Configuration module for Portuguese Parliament ETL Pipeline.

Defines legislature data sources, paths, and ETL settings.

Frederico Muñoz <fsmunoz@gmail.com>
"""

from pathlib import Path
from typing import TypedDict

## Config class
class LegislatureConfig(TypedDict, total=False):
    """Configuration for a single legislature."""
    url: str
    info_base_url: str
    atividades_url: str  # Optional: URL for Atividades dataset
    name: str
    start_date: str


# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
CAP_SOURCE_DIR = DATA_DIR / "cap_source"  # Committed CAP mapping CSVs from votoaberto-cap

# Ensure directories exist
BRONZE_DIR.mkdir(parents=True, exist_ok=True)
SILVER_DIR.mkdir(parents=True, exist_ok=True)
CAP_SOURCE_DIR.mkdir(parents=True, exist_ok=True)

# Legislature configurations (last 3 legislatures only).
#
#I've kept the same structure a previously used in the proc-parl-pt
# project, mostly

LEGISLATURES: dict[str, LegislatureConfig] = {
    "L17": {
        "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=vT4NKYCAcAkVhsxkek0X9GR7eZ0OofLhvaamIHFKZGIIYlhnxu7zKIsblH59KL72h98Zu1N1YTqN8DXZMgmt3EbdPgzlwhrmIMsaAAVbmHdJph0ajupa9JllbEogo%2fqScLfsVIOicGp1PUvXnG1iXa7YUCL7474EaFm4dv0QL6fNQlcFkI97C0SXv5ry3OgJC8HCmkJqINrPay1OF9uNI4iJaHCchWhK0Z2ojcLFwyJz7YF0bimXQgilgr3eE5OFAFyTax77Lv8ioecHw7ZXt%2fJppcfvF0%2bPRnNoPelExY4Q36mLd%2fmOQxfNwa3clarGoyTjcrzuDlexcc%2bpWM0RUy51EQt2FjJqLFwjbLFDw2E%3d&fich=IniciativasXVII_json.txt&Inline=true",
        "info_base_url":"https://app.parlamento.pt/webutils/docs/doc.txt?path=5zyAbVC5P5iHxLFX4dvvYn4459K3M9lWQH%2fDcO4IKLXMkN5Hq425yPeRcYFgb%2bc9DlwE0R6cUU5It3LijJBhLPUtaTjLFF9s8dGGHH0M4uqbYAe%2fs5fZg%2fUtcGhKciBr2UtOK4Ni3dUZ7gP9e5liyqHrAZAq7gSTC0sOd09nqPmhcE4irF1LnPUOWEkBTMZ0vShEUbCe7xVRvZrVB92ezvEC1kU%2bR97%2f0dzjL1wDss6Axa1dI2UbSwuzK3uQ3NGl%2feA6BlJaGr3k3zpVIsFoUskWmsgn6ZiIAfMLO1mKE8pmm%2bwMQT7ymW8%2bOSPw51PEFpUPFEU6KqvWL%2bkPKgv9qt4MytM%2fqFtBAbe4DDF%2f3sXzYYGU6GO2UASQhaA2ESwUMofHxV52YK52uXEunzHZZg%3d%3d&fich=InformacaoBaseXVII_json.txt&Inline=true",
        "atividades_url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=MvC%2beisjw0NRM%2b5VPH%2bMQs5Gt2qv74TPZF5glj1aifwO0zMmLlbffto8DV6i%2bOqsFwvUGB1aoK1MS0SUSBj6QdbFHywkApglmKeKfi2BmkQARJ5ySv5SIETQTYxHz5PxIX%2fGM693nC1O0q4rroauUdKupOi8zzMeCFNuYpl6Kt1BTDwkV%2fBz%2fHQg8JCYa5Jauy53%2bdAiC2ePgjFzCqAK8HZHByoUg0bgVvKEBzx4VzNV0dXT1JM6UaKOI3DxVyer61k2d6PBzqopQNLIcybR%2fjqPwQopwp58n3uXv1x3sAEhwsNyV8rVL%2bAuz%2biUEk1Y%2bb6mW2UH0SsJCHdsEq150IMI6F1Qp9kEPjopgvYcqgQmjbMlqAEmnSNn6kleSQm4&fich=AtividadesXVII_json.txt&Inline=true",
        "name": "XVII Legislatura",
    },
    "L16": {
        "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=IIDQnqbDLG0A0muO1xMUgrs%2fPw6vFjR%2bW97rDQOmkvZbeKW4ZQ%2fM6wYlQCDss0%2f4%2fvXPNLBeth1oEAXy2vD2RcNhc%2bodqFDeNF%2fXBt5kdVV9v1nhDUmdUGhJCErURltdyfMszVP6fAeur32lcwl5B48p6J5Hr6MxxstVrDuntnOG0sXqhdg9E7I9tkxORKo%2fHwmWTPhn6kf7kwU%2bvvdnY40YolLKyFouuZG8CH0TFuwTHeT8rarQ%2bVH7Gx2AdAcqHa0NOWQqBsmHcWUuccR0yWOAKZar%2bOXJ77QPFMatmlHa2v3NpbCPhtwyLWNG6LVGRukBq5VW6fUw63DDIqi6QiwtQBHtyQfvnbI91xbVOk8%3d&fich=IniciativasXVI_json.txt&Inline=true",
        "info_base_url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=4Sf%2bxPAhVpNaP72V4A4iR827KnpDLDkMYQNE9oZlXc1MZnlNq4dbG7iQtxDaIvcg%2fuJcSweOzCu%2fcnh4%2fW38SKiZpsyKLhixxeW7aqdvPBFAB9TjcIL%2f2xzZ0uhVt5S%2b%2bygk8bFneqEQZCn6afycBtYH6tLqpwfi%2ffntls6d%2fJaoNlGYhP%2bVp38jZKOXyGyyh%2bD7ZD6gr%2fd7HyUvWY692KJAx11fbcLI4jqWAoq0Wv4OT7b1owEhcx0Wyj6%2fmCVtoZ0o6OIjYiHf2KMMN6jR%2b64v5iTlzdnOPydP5QKWBu%2bpAPaKx3RDkHuDMzS0pxsYqDKNt47p8aIAWsLt7riwLQ7IwdOfgpJCmVQUmg1sLJ2%2bLGWaYwC0xujg3RkJuoMf6N0mGpNBcaKp0zooImL4OVK3WbpHvI0LmWQKClmkpmU%3d&fich=InformacaoBaseXVI_json.txt&Inline=true",
        "atividades_url":"https://app.parlamento.pt/webutils/docs/doc.txt?path=UBCB0Xox6y%2fUswON20%2f%2foNoouvOWZuTHVHUTTyDdqedMkjJSecj67LC4Wuz3rysEBYEktHIK7INQVEHKkXXPBimOBMjLkfRrohSLlIgTa05wMe%2fCRDm9vrNNQmrk6a3HU05f4NgUaYdRSjCiganwrtUHIlNi7CMPw%2frX0qqQrWEo4CgvItbCCUmYxUQd8DQX7DmOk0PHoBh0d7h9aYN%2b5%2b5r4oJylOvewKrTxoeeXa1Ih2NBKHXQAw9En5elMVkE1ztCuEn%2bqMvHChMVkd4yOoheXTO1hvawVNWs9n7OyKM4H6kc0xx%2beJ7zWwZKJUc8nKdDcPEVU0wDmSTj2pAiPliE9%2bRdAQQWazF5cSqbqT9bM6bsCWQVjRadJDI7FY9V&fich=AtividadesXVI_json.txt&Inline=true",
        "name": "XVI Legislatura",
    },
    "L15": {
        "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=Q9pMXr%2bqmsb6iUuOjta9OFE7aYcC8azZAkR6W%2b02QwrKJNaPcHmZdjTTcRlbVxB9Mh91Mj0fVKExPiqZdvwU6BQRNlWwvsde%2bl0ZCIE6suWvw8i7cfYmRF4bOXl9qGdTzxAF2EBjAGBj29G86CW%2feYOHacU6CWLTdQOjXnXM1AWHxrkcDHNCLG16jt8tGKnJ7XFSF3yDmLlzs8qJZOJHHrRsUhgegcYnTlQANJetzeF3iXdPG0gXyHoZba0CL%2faQIlmBWYkzidqBifcY3HjCuJtByK0y1CTbUIkD68c2NiUrwvTLbp7mht5IWPtSKX4UFypRjT9xDURYk397798qmY6gWNvrLN20AGCAniw6fJwAklrpWnx0ct9XN%2bHXeDOU&fich=IniciativasXV_json.txt&Inline=true",
        "info_base_url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=%2fRP9RO9rRG7Rm2x0b54LW2ok9tPweEYB90hne8Wjd7vjX8D7jtU3FOWvke8RG36EYJwz4fhE6CKgw7fC6NYMpNUEt3sFby%2bkJjnsEKK6K1WVmdZiEQDbSvvZZn%2bGThXS2icO46EPuJTta%2bxSZiIe6SWPokoOLzPBb7r4gt6lmRqfqYWseg7SippIjylziooXXpKET7PxF%2bO3naw1MimMO6WckMD%2fWdssGBVqCMPoFuxxQMhxtd7YaNTZSM0NHzFFycQlRkpc1sTaWGUnSivmaYfekteXanFSABHsyraj6TmiYUfkOBBZwvwvSQz9V7UN8iHsI%2fiUmWkC%2fU7fGOn490EUsGaZBrqqOqN1GlNTMbJy2bHO33N2jRRk9rIgJY8lTt39oD4102kaIMIoG18VLsJALZezTU9%2fJdyrbIpCgdE%3d&fich=InformacaoBaseXV_json.txt&Inline=true",
        "atividades_url":"https://app.parlamento.pt/webutils/docs/doc.txt?path=sUK2je6tIQzhF6ryiHFFlF6vPyB1NtvJn%2fn2QugHOPoqyjNvaqvW11W1H07WMc%2f%2bBO4gGlswtMZIlRsC6b4lhuE0zfBaJAjUHkqiAzkYapGmbEOfrPetpf3XJhXBzq%2b7jzY7FXKehZ9up0DHliBDAq5IC2aCjj7WEE%2foAzeSFU6R4iPEVNWMcTiTt4ZDdkV0qBUZg2vISHo9vugY6sUSzVD3HJo0Aj70YdBjQ5%2firWYkJFm%2fx7oSYvO04hD0QtmwoXuwZsX%2fbhlIKP9ctPLf5bYK%2bYdzSF86X6rb5oDBT68fm2kIAeurxFf1U603Y6E%2fInuJjUqGvFfZcYT%2fAHry5epTVedwqJkmuUuJqaVVXlc%3d&fich=AtividadesXV_json.txt&Inline=true",        
        "name": "XV Legislatura",
    },
    "L14": {
        "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=MRjU53F1NvJNWzaXbrTaBwlRPxSTJfGM23hrjAbamr1%2fGkZByUQKA5KmsNdKx%2f37mLg%2f2Bg3YXydGBLd0NR8D1s7u%2fTjkiqHb%2fMlZvh8HRjiJPXUJsqSyDGWfccdQvIdFdbiW3GLj5%2f3C4%2blTfuiV4dM8DLzSF6r9H6rz3biARbJDOFsijstFhz4v8nn2jiY8ubvqJGnBNeHOGOPeMenz%2bgUlBbAIM4Cx8xTW2rhLuooDcO3beOQPpIG4RXMJdSE2hvyAG8aatvy87kttJVwi72DL3L6HbNH4lbb6nHcSuBwmFcdPF9Ri60XecvhFAk1KMyX7cEBpQXj%2fdk%2fX4%2fr6sdiINnBCO8ddonqxWe1TQQ%3d&fich=IniciativasXIV_json.txt&Inline=true",
        "info_base_url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=wl%2bCUVeNARn8NII4gzkjnFxECAykhAfVKdWWu%2fQ%2bLsq5I%2fjKgdZlFxk6POdaaIeg2GTjhOCt2cAMVffKZCT%2bs%2bUczi81zND7N6%2fRFOuHMFSgscK%2fZ%2bZet5umJOu6%2bS8W1MK0j3wTmJn%2fjz6PUe5uCYM4ukhvVT7nI0P2Ab4Kl8NWmNPu6coddXkBm2JmvnR1KTFTSHb6b2eGjLEH4r89hoJKaIa8iSUM1Cqr%2fnOwG7K6lrnkqQIIyBhxLgnFQXU1Ag7461cBDgfRbqbl43O2EFWNgq9Litr4EOqxEwpgw86E8jQapZvfRDV4hchQ3VnFD1e%2bK63mS33HrzV9sYHsGz7YvxPq8rVaYuGsMlFmdavSX96opQWtEOe6gVe2J6uRYzMWCG66Yf%2b8TvAaOXV2kw%3d%3d&fich=InformacaoBaseXIV_json.txt&Inline=true",
        "atividades_url":"https://app.parlamento.pt/webutils/docs/doc.txt?path=wrHIx6hw4gdL8TK%2bqG4og5oeTi0EldUJ0HgV%2f0CVLcSf%2bxEyKAegJtZ25NOIzP3wkpI2P2SQfBWmUH9QyO%2fiO7tE4ZreaRhi8D0ub7QrHRYld9LZ92P8we3cFagApHPC9%2bdnm0%2fHH%2bQgeqyr%2bK1dTiw%2burOBVXi5mz0rLVXHbnTf36lGnzaHa33RYOC0WNTV3gaJX18s%2bsArxF%2fpQOKHaq1jpK%2f2%2bDbseB452IuwH1P34IwZxQus3LxzXbrEzQ6%2blhEASMLHyIbN8LS9ygK34Vn%2fOyGyL81iaQSUlUpIdJEY8UQXl93Y1uOAcKSTLbbAjIBSfJ52WZBq9Xi8J9ZFmb%2bVoGIuNw9GkQg6on2x0WAysRDHS765di3UyW6nOutv&fich=AtividadesXIV_json.txt&Inline=true",
        "name": "XIV Legislatura",
    },
    "L13": {
        "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=Ypnni2nk15MmdzsLUCNnzk3HqH%2bSpA06jaJQUGUlkHhFkNpwWtAseR2%2fd%2fQVRWbx96r0SNiptcYof4CH34vugxUX3aXWcEprwl0b2vpuWpxxbf%2bqX9W1gVYLF5vAWK12d89MrS4EcnxLGWyLVyQvU4QVTJEIXGqJB6PcKBNgr2aPLMI%2fd8AvgzfJxYz0a9rfWGWoZq7CFsIs9G5UMsCfYJuCXGm5KsA5ndK2M9%2br62dVqYEKj4hvA5iIK0MEIfEW0Gax8s0upE1xOfV080bIvhFmc1o%2bzHbteFNLrJ3apqXpx3nQ5j1f0UmwvIw5NfUC587ZLKtOXDllCzJhbcqbgeHa9el5f2lnLxk0aefDxtI%3d&fich=IniciativasXIII_json.txt&Inline=true",
        "info_base_url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=1fFtAGzcqAVNCL5ntGWSWjHqHyUv%2fnsFh5TgYYKaPg2JtxSiXISgegcq2iTto5H7LYUJLX2DNMwmb4dXJWSZLp5cBsIz7rg%2bzN9lGICqEJlZUzRXd9RKhghioEX1JJ%2b7rs%2bHCIoQxuZu6jUicrgREn2nov9uek8Q7KXztTvyi51oIc2ijzZT0BK3wg3Cg%2bOIqvSvq8XAeWjN0QSgfZc7681u%2f1djiYGcK0r5OAyIhdk7YCfHfFGLDxXinP5ZP5wlVJL41d31C8qUrs0MqGZbiTPf8abkpAh7ipBxGzDiL4KQ9wQGbGKL34oAmroGS3t5mlVzKiySkhKzLpz7knxbDVW%2bHQzQ5krujtUOk01B1PGMWHvV301mGGqPir2q1%2bfE&fich=InformacaoBaseXIII_json.txt&Inline=true",
        "atividades_url":"https://app.parlamento.pt/webutils/docs/doc.txt?path=8Gmmu%2bhFZ2PbeWbuVxB6wxJ%2b1WTaj21hLbDgHIkQDxMthx%2fSlS7xhV6JuazGbYAAfrfp2H946%2bmxZlpWoTi2rayZG1i8adxn7NAeFGVcdmEslEbyYRZOqA59jO8Z1DUL6yVaeUKicQjn9NIw3KR8kza%2fMBS%2bvZ2M7SuemdRq7U2EDQ8%2ffSr4BMtuhWnSpNawi0u9FhIlaOPsdzDpsEXnXnc4lq90U%2fAZYwGy8JfLICWvzJ4Og62JxuJVd4ouQqGF1GkBYSNMojcN8eWdK7CVnnWomw7l9V%2bgYY3BrhWTWVRucb%2bN%2b6C2GGFwOx9t0Q8P%2ftcLF1JmZ48rC0f6F1r1XwXh4PdRKyzL2zSSgzi9zYCmC3TChTHUR4d2ArJDra%2bP&fich=AtividadesXIII_json.txt&Inline=true",
        "name": "XIII Legislatura",
    },    
}

# Orçamento do Estado: propostas de alteração, one JSON file per budget year (from
# parlamento.pt/Cidadania/Paginas/DAOE.aspx). Fetched and transformed together with
# their legislatura (so `-l L17` refreshes OE2026 and OE2027). OE2022 is the XV one:
# the XIV file is empty (that budget was rejected on generalidade). ini_id is the budget bill
# (Proposta de Lei) in iniciativas.
OE: dict[int, dict[str, str]] = {
    2027: {"ini_id": "377352", "legislatura": "L17", "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=%2b5L7n2V3isPfnmH2LKW0XER%2fEy5cEDLBav8%2b8NkV11Z%2bdUTV728Ds%2fN8od%2fW35opS5EH%2b9Im0cN1yFV77YKTAu170rlzx7ffR5Sp7Aouf9IjuQg8Kub4PUeDwt%2f3%2fmp8BaPFn0p76jC6uh7ljujiL4wZ8%2bfYF1OyPLhXjU9vQolArGXN4Q3WyDqCg4AJwNsgAgJpUm%2bo2hNpV6qqLoo%2bW2G6FLoc717TISPLHDSQUdDI6dQqefcbizy4xGd%2bGzi1Dc7Z1tFuY9ayV8Gk%2fk0K4aDrxAoXQQ7K3LLaxAPHHMAky4iaOcp8IzgEc0HPFYjsvsBCHakbd4dMMjXNQxne722JXIfKZ0jMSvkqX3fZ8kh3fzNPf4gcZn9yBJ6xW2DdaSZ%2fCI4VlVIs89n86bpOHQ%3d%3d&fich=OEPropostasAlteracao2027Or_json.txt&Inline=true"},
    2026: {"ini_id": "315671", "legislatura": "L17", "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=daiz9yjjo3Ns5UJJ5YGJF116IVgOA1lNtutSOJOftX99jrrSTGNyc0sveSIoMszRuyXCC6yxoadfOYTGaBK7UT5AwSf3MR2vG02FOMc4jIYt3dkGVFlwnCSPihpd5EMp0VTY5LCKjb2fFjIUyVXHsnLeys%2bP50A9oYNvyYjveUw0gnimeRUuPFcEjOH0sY6%2fFEvnDRUzkqhlhVhSIfIm%2byXZRyYswb1sxdM%2f3Av%2btuYaEsxyl1w3fwqIojzmW%2bG%2fhw3vhZL2l38q8ccGgOWxTWICz10I1FfKCkEht6tr6ST5bVWIBvw%2fTMDazj8zKbcLsqsZIAYBayNH4XPIUw5I9s9p3e3LtyzCj544ATzgyr7Awt5kWhOzAgJDuSWaQXDNyQO%2b5d2gNbSK3NxPyWfGCCvnit3854%2bkXSZq%2f251ZeKVlY66br3zUjVr4hMkZyTn&fich=OEPropostasAlteracao2026Or_json.txt&Inline=true"},
    2025: {"ini_id": "304233", "legislatura": "L16", "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=9O3C%2fclZhDs%2beqbAhoRPFW2sHw6a6TLnd7fLenwOk3P%2b3uH8Um3q21Ch2RoG1lO7odOmmMe12n003k0G39v%2fGHgHdqKcLjHvmQPLPvs7%2f%2b90JKLSSV%2fQwGoyki%2bW7XCL2m5%2baiGG7xytSi%2fgwbKJOYe3L8C2qsgKgOgayH3BtafI6qRbGWj1pYL5VQaNUECUyYWdvlWTa6%2f6MzNrZIb0M9Uk7F6rwaS5E7lZ16QhdRVann8nwKHwDx0I9g%2bSsMRc7E4TNK9rmfFgbKwqfl8bKWPkpKPEHBvrrvUrFznXJAjjn9Cm5l5CCuN0h7Tp%2fYyq6dAUBsLJTTsSmyUXwaMYZj9yl0l1Lcu4MJx1iVrs25jkKcef%2bEBIzJVl5BL%2bQOyHVQcM3IRZ6Xdj388rusIqNr%2bGynaFgBieWtARAFKvymo%3d&fich=OEPropostasAlteracao2025Or_json.txt&Inline=true"},
    2024: {"ini_id": "253373", "legislatura": "L15", "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=A1DTs0Y9xAxv%2f47Hu0HZQWeQqJpbAmhkGCdLjsidloSgIY39bkTUNIfoZEA4k5V48OEXnscukubpkp9OhItHXqja8%2fubhFJwgMyjjsoi8Q%2f%2bj3ykYGH8foC7134lc06eEA7f6vvuBndZhnxoT1SOBr1o0V9plqxJhGlFoC4RZgXJy%2bJioRRM%2b5y1zk4eqcp3QVNcNHlMncqPpdVLUJgMCRoiy62aIGViy2BI7BILLd1K%2fMXbxXHU1W1KtOseH6d7R3wnsh5fmRPajjIcVNhuO%2bMItGWqQnf3cPPCSMCt3oqqQL9tixIIC8Ok4dayquGFQMSx1Or%2fEmPxbwK%2bIkjGeVCrvoYTr1LUS0fSP370lmG3QlpahMZLpM7V89DW5e3XGktsmjue6l96toRqo97YdyHPRC5WulaqUG5gOeitubqcEwV%2bxfj76s3bnURVZm5z&fich=OEPropostasAlteracao2024Or_json.txt&Inline=true"},
    2023: {"ini_id": "152005", "legislatura": "L15", "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=F056tRdqRlneVpjWcEvroe%2ff%2fPo4WDLYIsqR6BRYFcpk9hH4Ami1IUxNC6eCbI0hns%2fgJeEPMsKqRbKgZcbmUYCbXQu1hPU6swpte6oEFAgv7NW%2fSko4g7hRfriEm3%2fXMbyX8sg7vLxpFfgBt4uHihIhZP55vK%2fHpfT4DFs64zHqwddAKMpNa%2fb4QMSQecNb81Cl3q5Ps7kIkOKGcb3Jk54wozp1XEFhXjFnjODMO9xFHLeEhRtvFAWpJJ2OCbuWbr18b4Y%2fWgWZrKq6hcLeFWS11W2QWjNAmimXroYjjtaVwuLdWt64xu87VDqwArHZQaQ%2bQd3X6bua2vMAGYryoUor68%2fwyNOC0%2fCTaAEZEPJ8XRAaKZ%2b3XoSft%2b6%2bnregie0rdNDDYn2PUye%2fJUxU7AOPj%2fpSFGmNf0gNvHQj5iE%3d&fich=OEPropostasAlteracao2023Or_json.txt&Inline=true"},
    2022: {"ini_id": "121394", "legislatura": "L15", "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=IfIq79uZowlbT0lyexZc%2fK%2f7bSRzl3qm%2f2gFcnJI7%2b%2bDx0qGPbhVJyZcbJGHCbbVNvrhojkGHmgnsFjgKYeVsnhWsTt5yEt0HHoUUOM3ABoz%2fZ3Hhj9jHPZ0FApGj77zxdn2BD9BXTHX%2fQWi2eNw7Zvdf7ltecUmCRXbVbMP%2bXRSuv4ddRdcvyvv7z90I1%2fq1qIJ%2bxL3E%2bx8MMzu68sKy6avo5tSDRiJzJaVFZ2Q3DDy8E4rWGgqoJzPokIOC4%2fTVpBJj3sPfTy25O45Vqg3xs507Z%2fpRgYIxOmF8uhYMD6fWOWAhY0I838rU6%2f3hi%2feTUPzqbbHW7SRmOWgHM0Lt3jW3Tksos8rx6fJi98dQ5rTZdJB1o4DJ1j7j0%2bQ7LzLa55cf6pdjznxkw0Ag1F%2bWTQGjc7eyxLqQsIp%2f4OCjcY%3d&fich=OEPropostasAlteracao2022Or_json.txt&Inline=true"},
    2021: {"ini_id": "45392", "legislatura": "L14", "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=Sw1ynKRz3N4qOiYSBfHk6s3EWZYJoOKkzSkfQBHfLNKKE7Nz%2f36y0BVBLNzg8vlump08drz5smkdmsUsPfeMlvolMDwgRUrcjhJXCa0qsUzR9qdVy5UAntdOLURV2RX7RMbPfjz7QMikPnDKlEcfxtZySZ%2f77p%2bxPdmnzyNvCBpct4t7CqpR5EyUrGReXjtUsQFU7IK5ztAuU%2fQJE%2bXqx4vwNjq8DFoifhLViwF4SuEJ2W0nwS5VK5YLhSvqA22P7vSaSBrhjdsTGZNmw7EuRcmvSmcVhKX%2b48DkhPwrycRh%2bUELyXLliRNCtlNCx1tRR6oju88sfyRt3Vb53lfVqPlJhWajXAIDAwZV3bxRCoxPY3GeOWJiIjRnffxq%2bQeUrw2a%2bhvJnqZVWoGgXHlH94rIifHBbRlCrGMQIapS%2bDncCsYknFVLhXzFnBckTV%2b%2f&fich=OEPropostasAlteracao2021Or_json.txt&Inline=true"},
    2020: {"ini_id": "44314", "legislatura": "L14", "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=3vjDrBdDT8IHQYzhH0YpBckh%2biZtn3Csq%2bA1bOCggjN3nU3eFTGOA64xXg4F5Ig%2fFqA6oAVSdBKNsE0iGX7P4tyum0058cX%2bGlKgXpQVnV79ED7s3xJvKDvrR%2fMcryHg6MDAFrrq7WP%2f7Iq7jVL8zbkjGJJKSiYknfb4SePpUZF7%2bROmnlzIIoO1uX1HvO5EgUUo%2fXkHOzeX%2fBpzMjFfEirbwNagUoTsqtBGol7nalc96yWPUgRdh4iWWiPlWOVoAkePqNGcB2jKPP90AD5IkMsOamAV0lnCeFc8K5ZbNz4BNfKjXjwXGkdjNyx%2fat39A14KCkQZ%2bU5kmT99qPYvMTKl0Lh9fqV3uhmaqPJIpC4NkIE2KOEoCstAWV%2bgf4R1b7SdJuloGPLopj7sz%2fHD9vzzqTTRa6QQsoYePpaMKVsPN7F8E9KeC7nfB8iT%2b48p&fich=OEPropostasAlteracao2020Or_json.txt&Inline=true"},
}

# Budget bills with no propostas de alteração (rejected on generalidade), for oe_orcamentos
OE_SEM_PROPOSTAS: list[dict[str, str | int]] = [
    {"ano": 2022, "legislatura": "L14", "ini_id": "121193"},
]

# HTTP settings
FETCH_TIMEOUT = 60
FETCH_RETRIES = 3
FETCH_RETRY_DELAY = 2  # seconds
USER_AGENT = "ParlamentoDB-ETL/0.1.0"

# DuckDB settings
DUCKDB_MEMORY_LIMIT = "4GB"
DUCKDB_THREADS = 4

# Parquet settings
PARQUET_COMPRESSION = "ZSTD"
PARQUET_ROW_GROUP_SIZE = 100000
