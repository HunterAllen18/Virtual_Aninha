import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Aninha Confecções - Gestão Oficial", layout="wide")

# Estilização CSS
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
# Mudança de segurança: Garantindo que a conexão seja estabelecida corretamente
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        # ttl=0 garante dados em tempo real
        return conn.read(ttl=0).dropna(how="all")
    except Exception as e:
        st.error(f"Erro ao ler planilha: {e}")
        return pd.DataFrame(columns=["id", "nome", "cor", "preco", "estoque", "tam", "foto"])

def atualizar_planilha(novo_df):
    try:
        conn.update(data=novo_df)
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

# --- CARREGAMENTO ---
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
        is_admin = (senha == "32500")

# --- LÓGICA PRINCIPAL ---
if not is_admin:
    st.header(f"Olá, {nome_user if nome_user else 'bem-vinda(o)'}! ✨")
    busca = st.text_input("🔍 Procurar peça...", placeholder="Ex: Camisa, Bermuda...").upper()

    if df_estoque.empty:
        st.info("Catálogo vazio.")
    else:
        df_f = df_estoque[df_estoque['nome'].astype(str).str.contains(busca, na=False)]
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
                        st.write(f"💰 **R$ {item['preco']:.2f}**")
                        st.caption(f"Tam: {item['tam']}")
                        
                        if item['estoque'] > 0:
                            if st.button(f"🛒 Adicionar {cor_sel}", key=f"b_{item['id']}"):
                                st.session_state.carrinho.append({"nome": f"{nome_p} ({cor_sel})", "preco": item['preco']})
                                st.toast("Adicionado!")
                    with c_img:
                        if item['foto']:
                            # Mudança aqui: use_container_width é o padrão novo
                            st.image(item['foto'], use_container_width=True)

        with col_carrinho:
            st.subheader("🛒 Carrinho")
            total = sum(item['preco'] for item in st.session_state.carrinho)
            for i, item in enumerate(st.session_state.carrinho):
                c1, c2 = st.columns([4, 1])
                c1.write(f"{item['nome']} - R$ {item['preco']:.2f}")
                if c2.button("🗑️", key=f"rm_{i}"):
                    st.session_state.carrinho.pop(i)
                    st.rerun()
            
            if st.button("🚀 ENVIAR PEDIDO"):
                if nome_user and st.session_state.carrinho:
                    resumo = "\n".join([f"- {it['nome']}" for it in st.session_state.carrinho])
                    msg = f"*PEDIDO ANINHA CONFECÇÕES*\nCliente: {nome_user}\n\n{resumo}\n\n*TOTAL: R$ {total:.2f}*"
                    st.markdown(f'<a href="https://wa.me/5581986707825?text={urllib.parse.quote(msg)}" target="_blank">WHATSAPP</a>', unsafe_allow_html=True)

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
