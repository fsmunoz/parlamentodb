"""
Configuration module for Portuguese Parliament ETL Pipeline.

Defines legislature data sources, paths, and ETL settings.

Frederico Muñoz <fsmunoz@gmail.com>
"""

from pathlib import Path
from typing import TypedDict

## Config class
class LegislatureConfig(TypedDict):
    """Configuration for a single legislature."""
    url: str
    info_base_url: str
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
        "name": "XVII Legislatura",
    },
    "L16": {
        "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=IIDQnqbDLG0A0muO1xMUgrs%2fPw6vFjR%2bW97rDQOmkvZbeKW4ZQ%2fM6wYlQCDss0%2f4%2fvXPNLBeth1oEAXy2vD2RcNhc%2bodqFDeNF%2fXBt5kdVV9v1nhDUmdUGhJCErURltdyfMszVP6fAeur32lcwl5B48p6J5Hr6MxxstVrDuntnOG0sXqhdg9E7I9tkxORKo%2fHwmWTPhn6kf7kwU%2bvvdnY40YolLKyFouuZG8CH0TFuwTHeT8rarQ%2bVH7Gx2AdAcqHa0NOWQqBsmHcWUuccR0yWOAKZar%2bOXJ77QPFMatmlHa2v3NpbCPhtwyLWNG6LVGRukBq5VW6fUw63DDIqi6QiwtQBHtyQfvnbI91xbVOk8%3d&fich=IniciativasXVI_json.txt&Inline=true",
        "info_base_url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=4Sf%2bxPAhVpNaP72V4A4iR827KnpDLDkMYQNE9oZlXc1MZnlNq4dbG7iQtxDaIvcg%2fuJcSweOzCu%2fcnh4%2fW38SKiZpsyKLhixxeW7aqdvPBFAB9TjcIL%2f2xzZ0uhVt5S%2b%2bygk8bFneqEQZCn6afycBtYH6tLqpwfi%2ffntls6d%2fJaoNlGYhP%2bVp38jZKOXyGyyh%2bD7ZD6gr%2fd7HyUvWY692KJAx11fbcLI4jqWAoq0Wv4OT7b1owEhcx0Wyj6%2fmCVtoZ0o6OIjYiHf2KMMN6jR%2b64v5iTlzdnOPydP5QKWBu%2bpAPaKx3RDkHuDMzS0pxsYqDKNt47p8aIAWsLt7riwLQ7IwdOfgpJCmVQUmg1sLJ2%2bLGWaYwC0xujg3RkJuoMf6N0mGpNBcaKp0zooImL4OVK3WbpHvI0LmWQKClmkpmU%3d&fich=InformacaoBaseXVI_json.txt&Inline=true",
        "name": "XVI Legislatura",
    },
    "L15": {
        "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=Q9pMXr%2bqmsb6iUuOjta9OFE7aYcC8azZAkR6W%2b02QwrKJNaPcHmZdjTTcRlbVxB9Mh91Mj0fVKExPiqZdvwU6BQRNlWwvsde%2bl0ZCIE6suWvw8i7cfYmRF4bOXl9qGdTzxAF2EBjAGBj29G86CW%2feYOHacU6CWLTdQOjXnXM1AWHxrkcDHNCLG16jt8tGKnJ7XFSF3yDmLlzs8qJZOJHHrRsUhgegcYnTlQANJetzeF3iXdPG0gXyHoZba0CL%2faQIlmBWYkzidqBifcY3HjCuJtByK0y1CTbUIkD68c2NiUrwvTLbp7mht5IWPtSKX4UFypRjT9xDURYk397798qmY6gWNvrLN20AGCAniw6fJwAklrpWnx0ct9XN%2bHXeDOU&fich=IniciativasXV_json.txt&Inline=true",
        "info_base_url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=%2fRP9RO9rRG7Rm2x0b54LW2ok9tPweEYB90hne8Wjd7vjX8D7jtU3FOWvke8RG36EYJwz4fhE6CKgw7fC6NYMpNUEt3sFby%2bkJjnsEKK6K1WVmdZiEQDbSvvZZn%2bGThXS2icO46EPuJTta%2bxSZiIe6SWPokoOLzPBb7r4gt6lmRqfqYWseg7SippIjylziooXXpKET7PxF%2bO3naw1MimMO6WckMD%2fWdssGBVqCMPoFuxxQMhxtd7YaNTZSM0NHzFFycQlRkpc1sTaWGUnSivmaYfekteXanFSABHsyraj6TmiYUfkOBBZwvwvSQz9V7UN8iHsI%2fiUmWkC%2fU7fGOn490EUsGaZBrqqOqN1GlNTMbJy2bHO33N2jRRk9rIgJY8lTt39oD4102kaIMIoG18VLsJALZezTU9%2fJdyrbIpCgdE%3d&fich=InformacaoBaseXV_json.txt&Inline=true",  
        "name": "XV Legislatura",
    },
    "L14": {
        "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=MRjU53F1NvJNWzaXbrTaBwlRPxSTJfGM23hrjAbamr1%2fGkZByUQKA5KmsNdKx%2f37mLg%2f2Bg3YXydGBLd0NR8D1s7u%2fTjkiqHb%2fMlZvh8HRjiJPXUJsqSyDGWfccdQvIdFdbiW3GLj5%2f3C4%2blTfuiV4dM8DLzSF6r9H6rz3biARbJDOFsijstFhz4v8nn2jiY8ubvqJGnBNeHOGOPeMenz%2bgUlBbAIM4Cx8xTW2rhLuooDcO3beOQPpIG4RXMJdSE2hvyAG8aatvy87kttJVwi72DL3L6HbNH4lbb6nHcSuBwmFcdPF9Ri60XecvhFAk1KMyX7cEBpQXj%2fdk%2fX4%2fr6sdiINnBCO8ddonqxWe1TQQ%3d&fich=IniciativasXIV_json.txt&Inline=true",
        "info_base_url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=wl%2bCUVeNARn8NII4gzkjnFxECAykhAfVKdWWu%2fQ%2bLsq5I%2fjKgdZlFxk6POdaaIeg2GTjhOCt2cAMVffKZCT%2bs%2bUczi81zND7N6%2fRFOuHMFSgscK%2fZ%2bZet5umJOu6%2bS8W1MK0j3wTmJn%2fjz6PUe5uCYM4ukhvVT7nI0P2Ab4Kl8NWmNPu6coddXkBm2JmvnR1KTFTSHb6b2eGjLEH4r89hoJKaIa8iSUM1Cqr%2fnOwG7K6lrnkqQIIyBhxLgnFQXU1Ag7461cBDgfRbqbl43O2EFWNgq9Litr4EOqxEwpgw86E8jQapZvfRDV4hchQ3VnFD1e%2bK63mS33HrzV9sYHsGz7YvxPq8rVaYuGsMlFmdavSX96opQWtEOe6gVe2J6uRYzMWCG66Yf%2b8TvAaOXV2kw%3d%3d&fich=InformacaoBaseXIV_json.txt&Inline=true",  
        "name": "XIV Legislatura",
    },
    "L13": {
        "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=Ypnni2nk15MmdzsLUCNnzk3HqH%2bSpA06jaJQUGUlkHhFkNpwWtAseR2%2fd%2fQVRWbx96r0SNiptcYof4CH34vugxUX3aXWcEprwl0b2vpuWpxxbf%2bqX9W1gVYLF5vAWK12d89MrS4EcnxLGWyLVyQvU4QVTJEIXGqJB6PcKBNgr2aPLMI%2fd8AvgzfJxYz0a9rfWGWoZq7CFsIs9G5UMsCfYJuCXGm5KsA5ndK2M9%2br62dVqYEKj4hvA5iIK0MEIfEW0Gax8s0upE1xOfV080bIvhFmc1o%2bzHbteFNLrJ3apqXpx3nQ5j1f0UmwvIw5NfUC587ZLKtOXDllCzJhbcqbgeHa9el5f2lnLxk0aefDxtI%3d&fich=IniciativasXIII_json.txt&Inline=true",
        "info_base_url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=1fFtAGzcqAVNCL5ntGWSWjHqHyUv%2fnsFh5TgYYKaPg2JtxSiXISgegcq2iTto5H7LYUJLX2DNMwmb4dXJWSZLp5cBsIz7rg%2bzN9lGICqEJlZUzRXd9RKhghioEX1JJ%2b7rs%2bHCIoQxuZu6jUicrgREn2nov9uek8Q7KXztTvyi51oIc2ijzZT0BK3wg3Cg%2bOIqvSvq8XAeWjN0QSgfZc7681u%2f1djiYGcK0r5OAyIhdk7YCfHfFGLDxXinP5ZP5wlVJL41d31C8qUrs0MqGZbiTPf8abkpAh7ipBxGzDiL4KQ9wQGbGKL34oAmroGS3t5mlVzKiySkhKzLpz7knxbDVW%2bHQzQ5krujtUOk01B1PGMWHvV301mGGqPir2q1%2bfE&fich=InformacaoBaseXIII_json.txt&Inline=true",
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
