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
        "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=dVKsAZ0sC%2fPjvBRSDh%2bcMRq0KX%2fMC0XZsmETg717LK%2foOpsU9UpvKw%2bXKIAMKiiI3RIIndL0CPKqP%2b5tz%2fu%2bdOxNiWdBVQl7hsx3ewC2Ex6G0gX5p%2f0vL2b4HsSfkmskT1zOosnK6e%2bySmWfVU8g4VnQRnwmkopoEKK1AKoCng74eJYNtvIegF5qaiAhJZ22T0Gb3wP54CqVZa6Ds3wlLcujRsdP1dKCfw3olRDx4XSqVxF0XsGVYeBvdONi%2fy%2bvepRb7%2fRo2J4u2k5p%2bc2sz2NWV%2b6Wu2PlJHQk1PyfdfjNwGFNQoJ30JbJuH%2bjlK1zA1%2b5M5WP0FwwMJffUIHqNTBOo8wPvQegcJXRYtxejkQ%3d&fich=IniciativasXVII_json.txt&Inline=true",
        "info_base_url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=AOlYo9f%2b%2bgJTKQdX9utiBMg7xBj%2fod%2ba%2fz0yyYjkVesKs%2bJPIKoQTAUvlKF8wLxwr%2b7glLsIheHB53N690CyV5osebZNp5OT6mklryDt1PK7ARHgT9zVFFXt%2ffHrX8qeeiVanSx1DnaXMLsQnfoyg7WQceVwlJX66%2bWMZ0cALP3O7e41domjqwCtaBhVYkkklWUEp3LHlGKJISqqD72oqdkjUnnPihsI2TUhaC2Bxu7ZpSSzVwjUHsEiSfBdMryb8CLwknp6Fd2axRp5F2CJqQDofHCQxVYYmtaP5xvNCvgCOU2TzM5UkftUux%2fXUe5Govon31arSHtMGBNebOYzoUcaDzaRTZF0ucBmZ%2fl5CyQaWLSct383Xg4EbjgGt1HH&fich=InformacaoBaseXVII_json.txt&Inline=true",
        "name": "XVII Legislatura",
        "start_date": "2025-06-03",
    },
    "L16": {
        "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=IIDQnqbDLG0A0muO1xMUgrs%2fPw6vFjR%2bW97rDQOmkvZbeKW4ZQ%2fM6wYlQCDss0%2f4%2fvXPNLBeth1oEAXy2vD2RcNhc%2bodqFDeNF%2fXBt5kdVV9v1nhDUmdUGhJCErURltdyfMszVP6fAeur32lcwl5B48p6J5Hr6MxxstVrDuntnOG0sXqhdg9E7I9tkxORKo%2fHwmWTPhn6kf7kwU%2bvvdnY40YolLKyFouuZG8CH0TFuwTHeT8rarQ%2bVH7Gx2AdAcqHa0NOWQqBsmHcWUuccR0yWOAKZar%2bOXJ77QPFMatmlHa2v3NpbCPhtwyLWNG6LVGRukBq5VW6fUw63DDIqi6QiwtQBHtyQfvnbI91xbVOk8%3d&fich=IniciativasXVI_json.txt&Inline=true",
        "info_base_url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=4Sf%2bxPAhVpNaP72V4A4iR827KnpDLDkMYQNE9oZlXc1MZnlNq4dbG7iQtxDaIvcg%2fuJcSweOzCu%2fcnh4%2fW38SKiZpsyKLhixxeW7aqdvPBFAB9TjcIL%2f2xzZ0uhVt5S%2b%2bygk8bFneqEQZCn6afycBtYH6tLqpwfi%2ffntls6d%2fJaoNlGYhP%2bVp38jZKOXyGyyh%2bD7ZD6gr%2fd7HyUvWY692KJAx11fbcLI4jqWAoq0Wv4OT7b1owEhcx0Wyj6%2fmCVtoZ0o6OIjYiHf2KMMN6jR%2b64v5iTlzdnOPydP5QKWBu%2bpAPaKx3RDkHuDMzS0pxsYqDKNt47p8aIAWsLt7riwLQ7IwdOfgpJCmVQUmg1sLJ2%2bLGWaYwC0xujg3RkJuoMf6N0mGpNBcaKp0zooImL4OVK3WbpHvI0LmWQKClmkpmU%3d&fich=InformacaoBaseXVI_json.txt&Inline=true",
        "name": "XVI Legislatura",
        "start_date": "2022-03-29",
    },
    "L15": {
        "url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=Q9pMXr%2bqmsb6iUuOjta9OFE7aYcC8azZAkR6W%2b02QwrKJNaPcHmZdjTTcRlbVxB9Mh91Mj0fVKExPiqZdvwU6BQRNlWwvsde%2bl0ZCIE6suWvw8i7cfYmRF4bOXl9qGdTzxAF2EBjAGBj29G86CW%2feYOHacU6CWLTdQOjXnXM1AWHxrkcDHNCLG16jt8tGKnJ7XFSF3yDmLlzs8qJZOJHHrRsUhgegcYnTlQANJetzeF3iXdPG0gXyHoZba0CL%2faQIlmBWYkzidqBifcY3HjCuJtByK0y1CTbUIkD68c2NiUrwvTLbp7mht5IWPtSKX4UFypRjT9xDURYk397798qmY6gWNvrLN20AGCAniw6fJwAklrpWnx0ct9XN%2bHXeDOU&fich=IniciativasXV_json.txt&Inline=true",
        "info_base_url": "https://app.parlamento.pt/webutils/docs/doc.txt?path=%2fRP9RO9rRG7Rm2x0b54LW2ok9tPweEYB90hne8Wjd7vjX8D7jtU3FOWvke8RG36EYJwz4fhE6CKgw7fC6NYMpNUEt3sFby%2bkJjnsEKK6K1WVmdZiEQDbSvvZZn%2bGThXS2icO46EPuJTta%2bxSZiIe6SWPokoOLzPBb7r4gt6lmRqfqYWseg7SippIjylziooXXpKET7PxF%2bO3naw1MimMO6WckMD%2fWdssGBVqCMPoFuxxQMhxtd7YaNTZSM0NHzFFycQlRkpc1sTaWGUnSivmaYfekteXanFSABHsyraj6TmiYUfkOBBZwvwvSQz9V7UN8iHsI%2fiUmWkC%2fU7fGOn490EUsGaZBrqqOqN1GlNTMbJy2bHO33N2jRRk9rIgJY8lTt39oD4102kaIMIoG18VLsJALZezTU9%2fJdyrbIpCgdE%3d&fich=InformacaoBaseXV_json.txt&Inline=true",  
        "name": "XV Legislatura",
        "start_date": "2019-10-25",
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
