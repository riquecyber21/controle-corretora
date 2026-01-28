import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Configurações de página
st.set_page_config(page_title="Gestão de Seguros - Henrique & Mãe", layout="wide")

# Conexão com o Google Sheets
# O Streamlit vai buscar o link da planilha nos "Secrets" que você configurou
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        # Tenta ler os dados da planilha configurada nos Secrets
        df = conn.read()
        if df is not None and not df.empty:
            df['Data Ordenação'] = pd.to_datetime(df['Data Ordenação'])
        return df
    except Exception as e:
        # Se a planilha estiver vazia ou der erro, cria um DataFrame padrão
        return pd.DataFrame(columns=["ID", "Origem", "Cliente", "Tipo", "Mês Referência", "Valor Corretora", "Minha Comissão", "Premiação", "Data Ordenação"])

def salvar_venda(origem, cliente, tipo, valor_base, data_venda, premiacao):
    df_existente = carregar_dados()
    venda_id = datetime.now().strftime("%Y%m%d%H%M%S")
    novos_lancamentos = []
    
    # Regra: PME (3 meses), outros (1 mês)
    parcelas = 3 if tipo == "PME" else 1
    
    for i in range(parcelas):
        data_parc = data_venda + timedelta(days=30*i)
        
        # Lógica de cálculo conforme solicitado
        if tipo == "Apoio":
            comissao = 0
        else:
            comissao = (valor_base * 0.30)
            
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
    
    df_final = pd.concat([df_existente, pd.DataFrame(novos_lancamentos)], ignore_index=True)
    conn.update(data=df_final)
    st.cache_data.clear()

# --- INTERFACE ---
st.title("💼 Gestão de Comissões (Cloud)")
st.write(f"Bem-vinda! Hoje é {datetime.now().strftime('%d/%m/%Y')}")

with st.sidebar:
    st.header("📝 Novo Lançamento")
    origem = st.selectbox("Origem do Seguro", ["NB Seguros", "Particular"])
    cliente = st.text_input("Nome do Cliente")
    tipo = st.selectbox("Tipo", ["PME", "Adesão", "PF", "Apoio"])
    
    if tipo == "Apoio":
        st.info("Tipo Apoio: O valor total deve ser inserido em 'Premiação'.")
        valor = 0.0
    else:
        valor = st.number_input("Valor da Proposta (Corretora)", min_value=0.0)
        
    premio = st.number_input("Valor/Premiação (Minha Parte)", min_value=0.0)
    data_venda = st.date_input("Data da Venda", datetime.now())
    
    if st.button("Registrar na Nuvem"):
        if cliente:
            salvar_venda(origem, cliente, tipo, valor, data_venda, premio)
            st.success("Dados salvos com sucesso!")
            st.rerun()
        else:
            st.error("Por favor, digite o nome do cliente.")

# --- DASHBOARD ---
df = carregar_dados()

if not df.empty:
    # Indicadores Rápidos
    c1, c2, c3 = st.columns(3)
    total_nb = df[df["Origem"] == "NB Seguros"]["Minha Comissão"].sum() + df[df["Origem"] == "NB Seguros"]["Premiação"].sum()
    total_part = df[df["Origem"] == "Particular"]["Minha Comissão"].sum() + df[df["Origem"] == "Particular"]["Premiação"].sum()
    
    c1.metric("Total NB Seguros", f"R$ {total_nb:,.2f}")
    c2.metric("Total Particular", f"R$ {total_part:,.2f}")
    c3.metric("Fixo Mensal", "R$ 3.000,00")

    # Edição de Dados
    st.markdown("---")
    st.subheader("✏️ Editar ou Corrigir Entradas")
    df_editado = st.data_editor(df, use_container_width=True, key="editor_global",
                               column_config={"ID": None, "Data Ordenação": None})
    
    if st.button("💾 Salvar Alterações na Planilha"):
        conn.update(data=df_editado)
        st.cache_data.clear()
        st.success("Planilha atualizada!")
        st.rerun()

    # Detalhamento Separado
    st.markdown("---")
    col_nb, col_part = st.columns(2)
    
    with col_nb:
        st.subheader("🏢 NB Seguros")
        st.dataframe(df[df["Origem"] == "NB Seguros"].drop(columns=["ID", "Data Ordenação"]), use_container_width=True)
        
    with col_part:
        st.subheader("👤 Particular")
        st.dataframe(df[df["Origem"] == "Particular"].drop(columns=["ID", "Data Ordenação"]), use_container_width=True)
else:
    st.info("Aguardando o primeiro lançamento para exibir os dados.")
