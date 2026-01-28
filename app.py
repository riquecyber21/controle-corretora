import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Configurações de página
st.set_page_config(page_title="Gestão de Seguros - NB & Particular", layout="wide")

# Conexão com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        # Puxa a URL configurada nos Advanced Settings (Secrets) do Streamlit
        url_planilha = st.secrets["connections"]["gsheets"]["spreadsheet"]
        # ttl=0 garante que ele sempre busque o dado mais recente da planilha
        df = conn.read(spreadsheet=url_planilha, ttl=0)
        
        if df is not None and not df.empty:
            # Garante que a coluna de ordenação seja tratada como data
            df['Data Ordenação'] = pd.to_datetime(df['Data Ordenação'])
            return df
        return pd.DataFrame(columns=["ID", "Origem", "Cliente", "Tipo", "Mês Referência", "Valor Corretora", "Minha Comissão", "Premiação", "Data Ordenação"])
    except Exception:
        return pd.DataFrame(columns=["ID", "Origem", "Cliente", "Tipo", "Mês Referência", "Valor Corretora", "Minha Comissão", "Premiação", "Data Ordenação"])

def salvar_venda(origem, cliente, tipo, valor_base, data_venda, premiacao):
    df_existente = carregar_dados()
    venda_id = datetime.now().strftime("%Y%m%d%H%M%S")
    novos_lancamentos = []
    
    # Regra: PME (3 parcelas), outros (1 parcela)
    parcelas = 3 if tipo == "PME" else 1
    
    for i in range(parcelas):
        data_parc = data_venda + timedelta(days=30*i)
        
        # Tipo Apoio não calcula 30%
        comissao = 0 if tipo == "Apoio" else (valor_base * 0.30)
            
        novos_lancamentos.append({
            "ID": venda_id,
            "Origem": origem,
            "Cliente": cliente,
            "Tipo": tipo,
            "Mês Referência": data_parc.strftime("%m/%Y"),
            "Valor Corretora": valor_base,
            "Minha Comissão": comissao,
            "Premiação": premiacao if i == 0 else 0,
            "Data Ordenação": data_parc.replace(day=1).strftime('%Y-%m-%d')
        })
    
    # Junta os novos dados aos antigos
    df_final = pd.concat([df_existente, pd.DataFrame(novos_lancamentos)], ignore_index=True)
    
    # Salva de volta no Google Sheets
    url_planilha = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn.update(spreadsheet=url_planilha, data=df_final)
    st.cache_data.clear()

# --- INTERFACE ---
st.title("💼 Gestão de Comissões Profissionais")

with st.sidebar:
    st.header("📝 Novo Lançamento")
    origem = st.selectbox("Origem do Seguro", ["NB Seguros", "Particular"])
    cliente = st.text_input("Nome do Cliente")
    tipo = st.selectbox("Tipo", ["PME", "Adesão", "PF", "Apoio"])
    
    if tipo == "Apoio":
        st.info("Apoio: Coloque o valor total em 'Premiação'.")
        valor = 0.0
    else:
        valor = st.number_input("Valor da Proposta", min_value=0.0)
        
    premio = st.number_input("Valor/Premiação (Sua Parte)", min_value=0.0)
    data_venda = st.date_input("Data da Venda", datetime.now())
    
    if st.button("Registrar na Nuvem"):
        if cliente:
            salvar_venda(origem, cliente, tipo, valor, data_venda, premio)
            st.success("Salvo no Google Sheets!")
            st.rerun()
        else:
            st.error("Digite o nome do cliente.")

df = carregar_dados()

if not df.empty:
    # --- DASHBOARD ---
    c1, c2, c3 = st.columns(3)
    total_nb = df[df["Origem"] == "NB Seguros"]["Minha Comissão"].sum() + df[df["Origem"] == "NB Seguros"]["Premiação"].sum()
    total_part = df[df["Origem"] == "Particular"]["Minha Comissão"].sum() + df[df["Origem"] == "Particular"]["Premiação"].sum()
    
    c1.metric("Total NB Seguros", f"R$ {total_nb:,.2f}")
    c2.metric("Total Particular", f"R$ {total_part:,.2f}")
    c3.metric("Fixo Mensal", "R$ 3.000,00")

    # --- EDIÇÃO ---
    st.markdown("---")
    st.subheader("✏️ Editar Entradas")
    df_editado = st.data_editor(df, use_container_width=True, key="editor_mae",
                               column_config={"ID": None, "Data Ordenação": None})
    
    if st.button("💾 Salvar Alterações"):
        url_planilha = st.secrets["connections"]["gsheets"]["spreadsheet"]
        conn.update(spreadsheet=url_planilha, data=df_editado)
        st.cache_data.clear()
        st.success("Alterações sincronizadas!")
        st.rerun()

    # --- DETALHAMENTO ---
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏢 NB Seguros")
        st.dataframe(df[df["Origem"] == "NB Seguros"].drop(columns=["ID", "Data Ordenação"]), use_container_width=True)
    with col2:
        st.subheader("👤 Particular")
        st.dataframe(df[df["Origem"] == "Particular"].drop(columns=["ID", "Data Ordenação"]), use_container_width=True)
else:
    st.info("Bem-vinda! Registre a primeira venda no menu lateral para começar.")
