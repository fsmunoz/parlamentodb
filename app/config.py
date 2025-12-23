"""FastAPI application settings.

Frederico Muñoz <fsmunoz@gmail.com>

Uses pydantic-settings (https://docs.pydantic.dev/latest/concepts/pydantic_settings/) for
configuration management with environment variable override support. Pydantic comes with FastAPI.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # API metadata, need to be updated when we change things...
    API_TITLE: str = "Portuguese Parliament API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = """
API REST para dados do Parlamento / REST API for Portuguese Parliament data (Assembleia da República).

**2025, Frederico Muñoz**

### [PT] Introdução

Esta API fornece acesso estruturado a dados da Assembleia da
República, utilizando os [Dados
Abertos](https://www.parlamento.pt/Cidadania/paginas/dadosabertos.aspx)
oficiais.

Segue a convenção de usar **inglês para elementos técnicos**
(por exemplo, infraestrutura e nomes internos) e **português para
conceitos do domínio**, alinhado com as fontes de dados
originais (e.g. *legislatura*, *deputados*, *iniciativas*).
    
A documentação abaixo mantém os nomes e descrições do domínio em
português quando apropriado, sem tradução completa da interface.

---
    
### [EN] Overview
    
Provides structured access to:
    
- **Iniciativas**: Legislative initiatives (bills, resolutions, etc.)
- **Atividades**: Legislative activities (condemnation votes, etc.)    
- **Votações**: Voting records with results, for both initiatives and activities
- **Legislaturas**: Legislature metadata (number of deputies, parliamentary groups)
- **Deputados**: information on MPs (personal information, status, circle)
- **Círculos**: electoral circles (general information, MPs elected by circle)    

"""

    # Pagination
    DEFAULT_LIMIT: int = 50
    MAX_LIMIT: int = 500

    # Data paths
    DATA_DIR: str = "data/silver"

    # DuckDB
    DUCKDB_MEMORY_LIMIT: str = "4GB"
    DUCKDB_THREADS: int = 4
    DUCKDB_QUERY_TIMEOUT: str = "30s"  # Query timeout (30 seconds)

    # NOTE: CORS is handled by Cloudflare/nginx in production.
    # For local development, add CORSMiddleware directly in main.py if needed.
    # See DEPLOYMENT.md for infrastructure configuration.

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# Global settings instance
settings = Settings()
