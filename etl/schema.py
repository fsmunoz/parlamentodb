"""Schema definitions and field name normalization.

Frederico Muñoz <fsmunoz@gmail.com>

The Portuguese Parliament API uses PascalCase field names, recently,
but depending on the legislature it can vary: we normalize to
snake_case for consistency and Python conventions. All nested
structures are preserved in their original form, so they might vary
from legislature to legislature - which is why we avoid outputting
nested structs.

"""

# Field name mapping (PascalCase -> snake_case)
FIELD_MAPPING = {
    # Core initiative fields
    "IniNr": "ini_nr",
    "IniTipo": "ini_tipo",
    "IniDescTipo": "ini_desc_tipo",
    "IniLeg": "ini_leg",
    "IniSel": "ini_sel",
    "IniTitulo": "ini_titulo",
    "IniTextoSubst": "ini_texto_subst",
    "IniLinkTexto": "ini_link_texto",
    "IniId": "ini_id",
    "IniEpigrafe": "ini_epigrafe",
    "IniObs": "ini_obs",
    "IniTextoSubstCampo": "ini_texto_subst_campo",

    # Dates
    "DataInicioleg": "data_inicio_leg",
    "DataFimleg": "data_fim_leg",

    # Nested structures (-> STRUCT/LIST types in Parquet)
    "IniAutorOutros": "ini_autor_outros",
    "IniAutorDeputados": "ini_autor_deputados",
    "IniAutorGruposParlamentares": "ini_autor_grupos_parlamentares",
    "IniAnexos": "ini_anexos",
    "IniEventos": "ini_eventos",
    "IniciativasEuropeias": "iniciativas_europeias",
    "IniciativasOrigem": "iniciativas_origem",
    "IniciativasOriginadas": "iniciativas_originadas",
    "Links": "links",
    "Peticoes": "peticoes",
    "PropostasAlteracao": "propostas_alteracao",
}


## Helpers

def get_select_clause(legislature: str) -> str:
    """
    Generate SELECT clause for DuckDB transformation.

    Args:
        legislature: Legislature ID (e.g., "L17")

    Returns:
        SQL SELECT clause with field mappings and metadata
    """
    selects = []

    # Add field mappings
    for old, new in FIELD_MAPPING.items():
        selects.append(f"{old} as {new}")

    # Add derived field: ini_data (date of first event - initiative submission date)
    # This is the minimum DataFase from ini_eventos array, representing when the
    # initiative was first "known" to parliament (typically the "Entrada" event)
    selects.append("""list_min(list_transform(IniEventos, x -> x.DataFase)) AS ini_data""")

    # Add metadata fields
    selects.append(f"'{legislature}' as legislatura")
    selects.append("CURRENT_TIMESTAMP as etl_timestamp")

    return ",\n            ".join(selects)


def normalize_field_name(name: str) -> str:
    """
    Normalize a field name to snake_case.

    Args:
        name: Original field name

    Returns:
        Normalized field name
    """
    return FIELD_MAPPING.get(name, name.lower())
