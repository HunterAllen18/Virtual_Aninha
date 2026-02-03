import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Aninha Confecções - Gestão Oficial", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0e1117; }
    .stButton>button { border-radius: 10px; background-color: #6c5ce7; color: white; width: 100%; }
    .product-card {
        border: 1px solid #333; padding: 20px; border-radius: 15px;
        background-color: #161b22; margin-bottom: 25px;
    }
    .delete-btn button { background-color: #ff4b4b !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        # Lemos os dados e forçamos o preenchimento de valores vazios para evitar o erro de numpy
        df = conn.read(ttl=0)
        df = df.dropna(how="all")
        # Converte coluna de preço para numérico e preenche erros com 0
        df['preco'] = pd.to_numeric(df['preco'], errors='coerce').fillna(0.0)
        # Garante que nome e cor sejam strings
        df['nome'] = df['nome'].astype(str).str.upper()
        df['cor'] = df['cor'].astype(str).str.upper()
        return df
    except Exception as e:
        st.error(f"Erro na leitura: {e}")
        return pd.DataFrame(columns=["id", "nome", "cor", "preco", "estoque", "tam", "foto"])

def atualizar_planilha(novo_df):
    conn.update(data=novo_df)
    st.cache_data.clear()
    st.rerun()

df_estoque = carregar_dados()

if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("𝓐ninha Conf.")
    nome_user = st.text_input("Seu Nome", "").upper()
    st.divider()
    with st.expander("🔐 Área do Administrador"):
        senha = st.text_input("Senha", type="password")
        is_admin = (senha == "1234")

# --- LÓGICA PRINCIPAL ---
if not is_admin:
    st.header(f"Olá, {nome_user if nome_user else 'bem-vinda(o)'}! ✨")
    busca = st.text_input("🔍 Procurar peça...", "").upper()

    if df_estoque.empty:
        st.info("Catálogo vazio.")
    else:
        # Filtro seguro
        df_f = df_estoque[df_estoque['nome'].str.contains(busca, na=False)]
        
        col_loja, col_carrinho = st.columns([2, 1])

        with col_loja:
            for nome_p in df_f['nome'].unique():
                variantes = df_f[df_f['nome'] == nome_p]
                with st.container(border=True):
                    c_img, c_info = st.columns([1, 1])
                    with c_info:
                        st.subheader(nome_p)
                        cores = variantes['cor'].unique()
                        cor_sel = st.selectbox(f"Cor:", cores, key=f"s_{nome_p}")
                        item = variantes[variantes['cor'] == cor_sel].iloc[0]
                        
                        # FORMATAÇÃO SEGURA DE PREÇO
                        preco_val = float(item['preco'])
                        st.write(f"💰 **R$ {preco_val:.2f}**")
                        
                        st.caption(f"Tam: {item['tam']}")
                        
                        if item['estoque'] > 0:
                            if st.button(f"🛒 Adicionar {cor_sel}", key=f"b_{item['id']}"):
                                st.session_state.carrinho.append({"nome": f"{nome_p} ({cor_sel})", "preco": preco_val})
                                st.toast("Adicionado!")
                    with c_img:
                        if item['foto'] and str(item['foto']).startswith('http'):
                            st.image(item['foto'], use_container_width=True)
                        else:
                            st.write("📦 Sem foto")

        with col_carrinho:
            st.subheader("🛒 Carrinho")
            total = sum(float(item['preco']) for item in st.session_state.carrinho)
            for i, item in enumerate(st.session_state.carrinho):
                st.write(f"{item['nome']} - R$ {item['preco']:.2f}")
            
            if st.button("🚀 ENVIAR PEDIDO") and st.session_state.carrinho:
                if nome_user:
                    resumo = "\n".join([f"- {it['nome']}" for it in st.session_state.carrinho])
                    msg = f"*PEDIDO ANINHA*\nCliente: {nome_user}\n\n{resumo}\n\n*TOTAL: R$ {total:.2f}*"
                    link = f"https://wa.me/5581999998888?text={urllib.parse.quote(msg)}"
                    st.markdown(f'<a href="{link}" target="_blank">WHATSAPP</a>', unsafe_allow_html=True)

else:
    # --- ADMIN ---
    st.title("⚙️ Painel Admin")
    t1, t2 = st.tabs(["📦 Estoque", "➕ Novo"])
    with t1:
        for idx, row in df_estoque.iterrows():
            with st.container(border=True):
                col_a, col_b = st.columns([4, 1])
                col_a.write(f"**{row['nome']}** ({row['cor']})")
                if col_b.button("Excluir", key=f"d_{row['id']}"):
                    atualizar_planilha(df_estoque.drop(idx))
    with t2:
        with st.form("n", clear_on_submit=True):
            f_n = st.text_input("Nome").upper()
            f_c = st.text_input("Cor").upper()
            f_p = st.number_input("Preço", min_value=0.0)
            f_e = st.number_input("Estoque", min_value=0)
            f_t = st.text_input("Tamanhos")
            f_f = st.text_input("Link Foto")
            if st.form_submit_button("Salvar"):
                novo = pd.DataFrame([{"id": str(len(df_estoque)+101), "nome": f_n, "cor": f_c, "preco": f_p, "estoque": f_e, "tam": f_t, "foto": f_f}])
                atualizar_planilha(pd.concat([df_estoque, novo], ignore_index=True))
