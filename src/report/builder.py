"""Construção dos entregáveis finais (Etapa 4).

- HTML → PDF via WeasyPrint (relatório + sumário)
- PowerPoint via python-pptx
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src import paths

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_relatorio_tecnico(contexto: dict, out_pdf: Path) -> Path:
    """Gera o Relatório Técnico Final em PDF a partir do template HTML."""
    raise NotImplementedError("TODO: render Jinja → WeasyPrint → PDF")


def render_sumario_executivo(contexto: dict, out_pdf: Path) -> Path:
    """Gera o Sumário Executivo (4-6 pgs) em PDF."""
    raise NotImplementedError("TODO: render Jinja → WeasyPrint → PDF")


def render_apresentacao(contexto: dict, out_pptx: Path) -> Path:
    """Gera a Apresentação Executiva (15-20 slides) em PPTX."""
    raise NotImplementedError("TODO: python-pptx a partir de um layout base")


def build_all(versao: str = "v1") -> dict[str, Path]:
    """Roda os três entregáveis e retorna os caminhos."""
    paths.ensure_dirs()
    contexto: dict = {}  # TODO: carregar de outputs/tabelas/ e outputs/graficos/
    out_dir = paths.OUT_RELATORIOS
    return {
        "relatorio": render_relatorio_tecnico(contexto, out_dir / f"relatorio-tecnico-{versao}.pdf"),
        "sumario": render_sumario_executivo(contexto, out_dir / f"sumario-executivo-{versao}.pdf"),
        "apresentacao": render_apresentacao(contexto, out_dir / f"apresentacao-{versao}.pptx"),
    }
