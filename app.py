import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Gestão Henrique - Google Sheets", layout="wide")

# URL da sua planilha (substitua pela sua)
URL_PLANILHA = "SUA_URL_DO_GOOGLE_SHEETS_AQUI"

# Conexão com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        df = conn.read(spreadsheet=URL_PLANILHA)
        if not df.empty:
            df['Data Ordenação'] = pd.to_datetime(df['Data Ordenação'])
        return df
    except:
        return pd.DataFrame(columns=["ID", "Origem", "Cliente", "Tipo", "Mês Referência", "Valor Corretora", "Minha Comissão", "Premiação", "Data Ordenação"])

def salvar_venda(origem, cliente, tipo, valor_base, data_venda, premiacao):
    df_existente = carregar_dados()
    venda_id = datetime.now().strftime("%Y%m%d%H%M%S")
    novos_lancamentos = []
    
    parcelas = 3 if tipo == "PME" else 1
    for i in range(parcelas):
        data_parc = data_venda + timedelta(days=30*i)
        comissao = 0 if tipo == "Apoio" else (valor_base * 0.30)
            
        novos_lancamentos.append({
            "ID": venda_id, "Origem": origem, "Cliente": cliente, "Tipo": tipo,
            "Mês Referência": data_parc.strftime("%m/%Y"), "Valor Corretora": valor_base,
            "Minha Comissão": comissao, "Premiação": premiacao if i == 0 else 0,
            "Data Ordenação": data_parc.replace(day=1).strftime('%Y-%m-%d')
        })
    
    df_final = pd.concat([df_existente, pd.DataFrame(novos_lancamentos)], ignore_index=True)
    conn.update(spreadsheet=URL_PLANILHA, data=df_final)
    st.cache_data.clear()

# --- INTERFACE ---
st.title("💼 Gestão Henrique & NB Seguros (Cloud)")

with st.sidebar:
    st.header("📝 Novo Lançamento")
    origem = st.selectbox("Origem", ["NB Seguros", "Particular"])
    cliente = st.text_input("Nome do Cliente")
    tipo = st.selectbox("Tipo", ["PME", "Adesão", "PF", "Apoio"])
    valor = st.number_input("Valor Proposta", min_value=0.0) if tipo != "Apoio" else 0.0
    premio = st.number_input("Valor/Premiação", min_value=0.0)
    data_venda = st.date_input("Data", datetime.now())
    
    if st.button("Registrar na Nuvem"):
        salvar_venda(origem, cliente, tipo, valor, data_venda, premio)
        st.success("Dados enviados para o Google Sheets!")
        st.rerun()

df = carregar_dados()

if not df.empty:
    # Dashboards e Indicadores
    c1, c2, c3 = st.columns(3)
    total_nb = df[df["Origem"] == "NB Seguros"]["Minha Comissão"].sum() + df[df["Origem"] == "NB Seguros"]["Premiação"].sum()
    total_part = df[df["Origem"] == "Particular"]["Minha Comissão"].sum() + df[df["Origem"] == "Particular"]["Premiação"].sum()
    
    c1.metric("Total NB Seguros", f"R$ {total_nb:,.2f}")
    c2.metric("Total Particular", f"R$ {total_part:,.2f}")
    c3.metric("Fixo", "R$ 3.000,00")

    # Edição Direta
    st.subheader("✏️ Editar Entradas (Salva direto na Planilha)")
    df_editado = st.data_editor(df, use_container_width=True, key="editor",
                               column_config={"ID": None, "Data Ordenação": None})
    
    if st.button("💾 Sincronizar Alterações"):
        conn.update(spreadsheet=URL_PLANILHA, data=df_editado)
        st.cache_data.clear()
        st.success("Planilha atualizada!")
        st.rerun()

    # Detalhamento Separado
    col_nb, col_part = st.columns(2)
    with col_nb:
        st.subheader("🏢 NB Seguros")
        st.dataframe(df[df["Origem"] == "NB Seguros"].drop(columns=["ID", "Data Ordenação"]), use_container_width=True)
    with col_part:
        st.subheader("👤 Particular")
        st.dataframe(df[df["Origem"] == "Particular"].drop(columns=["ID", "Data Ordenação"]), use_container_width=True)
      """Helper code used to generate ``requires.txt`` files in the egg-info directory.

The ``requires.txt`` file has an specific format:
    - Environment markers need to be part of the section headers and
      should not be part of the requirement spec itself.

See https://setuptools.pypa.io/en/latest/deprecated/python_eggs.html#requires-txt
"""

from __future__ import annotations

import io
from collections import defaultdict
from collections.abc import Mapping
from itertools import filterfalse
from typing import TypeVar

from jaraco.text import yield_lines
from packaging.requirements import Requirement

from .. import _reqs
from .._reqs import _StrOrIter

# dict can work as an ordered set
_T = TypeVar("_T")
_Ordered = dict[_T, None]


def _prepare(
    install_requires: _StrOrIter, extras_require: Mapping[str, _StrOrIter]
) -> tuple[list[str], dict[str, list[str]]]:
    """Given values for ``install_requires`` and ``extras_require``
    create modified versions in a way that can be written in ``requires.txt``
    """
    extras = _convert_extras_requirements(extras_require)
    return _move_install_requirements_markers(install_requires, extras)


def _convert_extras_requirements(
    extras_require: Mapping[str, _StrOrIter],
) -> defaultdict[str, _Ordered[Requirement]]:
    """
    Convert requirements in `extras_require` of the form
    `"extra": ["barbazquux; {marker}"]` to
    `"extra:{marker}": ["barbazquux"]`.
    """
    output = defaultdict[str, _Ordered[Requirement]](dict)
    for section, v in extras_require.items():
        # Do not strip empty sections.
        output[section]
        for r in _reqs.parse(v):
            output[section + _suffix_for(r)].setdefault(r)

    return output


def _move_install_requirements_markers(
    install_requires: _StrOrIter, extras_require: Mapping[str, _Ordered[Requirement]]
) -> tuple[list[str], dict[str, list[str]]]:
    """
    The ``requires.txt`` file has an specific format:
        - Environment markers need to be part of the section headers and
          should not be part of the requirement spec itself.

    Move requirements in ``install_requires`` that are using environment
    markers ``extras_require``.
    """

    # divide the install_requires into two sets, simple ones still
    # handled by install_requires and more complex ones handled by extras_require.

    inst_reqs = list(_reqs.parse(install_requires))
    simple_reqs = filter(_no_marker, inst_reqs)
    complex_reqs = filterfalse(_no_marker, inst_reqs)
    simple_install_requires = list(map(str, simple_reqs))

    for r in complex_reqs:
        extras_require[':' + str(r.marker)].setdefault(r)

    expanded_extras = dict(
        # list(dict.fromkeys(...))  ensures a list of unique strings
        (k, list(dict.fromkeys(str(r) for r in map(_clean_req, v))))
        for k, v in extras_require.items()
    )

    return simple_install_requires, expanded_extras


def _suffix_for(req):
    """Return the 'extras_require' suffix for a given requirement."""
    return ':' + str(req.marker) if req.marker else ''


def _clean_req(req):
    """Given a Requirement, remove environment markers and return it"""
    r = Requirement(str(req))  # create a copy before modifying
    r.marker = None
    return r


def _no_marker(req):
    return not req.marker


def _write_requirements(stream, reqs):
    lines = yield_lines(reqs or ())

    def append_cr(line):
        return line + '\n'

    lines = map(append_cr, lines)
    stream.writelines(lines)


def write_requirements(cmd, basename, filename):
    dist = cmd.distribution
    data = io.StringIO()
    install_requires, extras_require = _prepare(
        dist.install_requires or (), dist.extras_require or {}
    )
    _write_requirements(data, install_requires)
    for extra in sorted(extras_require):
        data.write('\n[{extra}]\n'.format(**vars()))
        _write_requirements(data, extras_require[extra])
    cmd.write_or_delete_file("requirements", filename, data.getvalue())


def write_setup_requirements(cmd, basename, filename):
    data = io.StringIO()
    _write_requirements(data, cmd.distribution.setup_requires)
    cmd.write_or_delete_file("setup-requirements", filename, data.getvalue())
