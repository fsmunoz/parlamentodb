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

# Ensure directories exist
BRONZE_DIR.mkdir(parents=True, exist_ok=True)
SILVER_DIR.mkdir(parents=True, exist_ok=True)

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
