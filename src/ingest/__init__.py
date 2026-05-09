"""Ingestão de microdados de fontes oficiais (IBGE, Receita Federal/Sebrae).

Cada submódulo expõe:
- `download(...)` — baixa o arquivo bruto para data/raw/<fonte>/
- `parse(...)` — converte o bruto para parquet em data/interim/
- `process(...)` — gera a base final padronizada em data/processed/

Uso esperado via CLI:
    python -m src.ingest.pnadc --trimestre 2024Q4
    python -m src.ingest.censo --tabela domicilios
    python -m src.ingest.mei --uf todos
"""
