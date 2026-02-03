import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Aninha Confecções - Oficial", layout="wide")

# Estilos para deixar o site com cara de App profissional
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0e1117; }
    .stButton>button { border-radius: 10px; background-color: #6c5ce7; color: white; width: 100%; }
    .product-card {
        border: 1px solid #333; padding: 20px; border-radius: 15px;
        background-color: #161b22; margin-bottom: 20px;
    }
    .delete-btn button { background-color: #ff4b4b !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM GOOGLE SHEETS (VIA SECRETS) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    # ttl=0 garante que o site sempre mostre o que acabou de ser cadastrado
    df = conn.read(ttl=0)
    return df.dropna(how="all")

def salvar_dados(novo_df):
    conn.update(data=novo_df)
    st.cache_data.clear()
    st.rerun()

# --- CARREAR DADOS ---
df_estoque = carregar_dados()

if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# --- SIDEBAR: CLIENTE E ADMIN ---
with st.sidebar:
    st.title("𝓐ninha Conf.")
    nome_cliente = st.text_input("Seu Nome", "").upper()
    st.divider()
    with st.expander("🔐 Painel Administrativo"):
        senha = st.text_input("Senha", type="password")
        is_admin = (senha == "32500")

# --- INTERFACE ---
if not is_admin:
    # --- VISÃO DO CLIENTE ---
    st.header(f"Olá, {nome_cliente if nome_cliente else 'seja bem-vinda(o)'}! ✨")
    busca = st.text_input("🔍 O que você procura?", placeholder="Ex: Camisa, Bermuda...").upper()

    if df_estoque.empty:
        st.info("Catálogo em atualização. Volte logo!")
    else:
        # Filtrar busca
        df_f = df_estoque[df_estoque['nome'].astype(str).str.contains(busca, na=False)]
        
        col_loja, col_carrinho = st.columns([2, 1])

        with col_loja:
            # Agrupar variantes pelo nome do produto
            for nome_p in df_f['nome'].unique():
                variantes = df_f[df_f['nome'] == nome_p]
                with st.container(border=True):
                    c_img, c_info = st.columns([1, 1])
                    with c_info:
                        st.subheader(nome_p)
                        cor_sel = st.selectbox(f"Cor:", variantes['cor'].unique(), key=f"s_{nome_p}")
                        dados = variantes[variantes['cor'] == cor_sel].iloc[0]
                        
                        st.write(f"💰 **R$ {dados['preco']:.2f}**")
                        st.caption(f"Tamanhos: {dados['tam']}")
                        
                        if dados['estoque'] > 0:
                            if st.button(f"🛒 Adicionar {cor_sel}", key=f"b_{dados['id']}"):
                                st.session_state.carrinho.append({"nome": f"{nome_p} ({cor_sel})", "preco": dados['preco']})
                                st.toast("Adicionado!")
                        else:
                            st.error("Esgotado")
                    with c_img:
                        if dados['foto']: st.image(dados['foto'], use_container_width=True)
                        else: st.write("📦 Sem foto")

        with col_carrinho:
            st.subheader("🛒 Carrinho")
            total = 0
            for i, item in enumerate(st.session_state.carrinho):
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{item['nome']}**\nR$ {item['preco']:.2f}")
                if c2.button("❌", key=f"r_{i}"):
                    st.session_state.carrinho.pop(i)
                    st.rerun()
                total += item['preco']
            
            if st.button("✅ Finalizar Pedido") and st.session_state.carrinho:
                if nome_cliente:
                    resumo = "\n".join([f"- {i['nome']}" for i in st.session_state.carrinho])
                    msg = f"*NOVO PEDIDO - ANINHA CONFECÇÕES*\nCliente: {nome_cliente}\n\n{resumo}\n\n*TOTAL: R$ {total:.2f}*"
                    link = f"https://wa.me/5581986707825?text={urllib.parse.quote(msg)}"
                    st.markdown(f'<a href="{link}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:12px; border-radius:10px; cursor:pointer; font-weight:bold;">CONFIRMAR NO WHATSAPP</button></a>', unsafe_allow_html=True)
                else: st.warning("Digite seu nome na lateral!")

else:
    # --- VISÃO DO ADMINISTRADOR ---
    st.title("⚙️ Gestão de Loja")
    tab1, tab2 = st.tabs(["📦 Estoque Atual", "➕ Cadastrar Novo"])
    
    with tab1:
        for idx, row in df_estoque.iterrows():
            with st.container(border=True):
                col_det, col_del = st.columns([4, 1])
                col_det.write(f"**{row['nome']}** ({row['cor']}) - R$ {row['preco']}")
                st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
                if col_del.button("🗑️", key=f"d_{row['id']}"):
                    salvar_dados(df_estoque.drop(idx))
                st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        with st.form("novo_prod", clear_on_submit=True):
            f_nome = st.text_input("Nome do Modelo").upper()
            f_cor = st.text_input("Cor").upper()
            c1, c2 = st.columns(2)
            f_preco = c1.number_input("Preço", min_value=0.0)
            f_est = c2.number_input("Estoque", min_value=0)
            f_tam = st.text_input("Tamanhos")
            f_foto = st.text_input("Link da Foto")
            if st.form_submit_button("💾 Salvar na Planilha"):
                novo = pd.DataFrame([{"id": str(len(df_estoque)+101), "nome": f_nome, "cor": f_cor, "preco": f_preco, "estoque": f_est, "tam": f_tam, "foto": f_foto}])
                salvar_dados(pd.concat([df_estoque, novo], ignore_index=True))

