import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import re

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Aninha Confecções - Vitrine", layout="wide")

# CSS para Customização e Ocultação do Perfil/Menu
st.markdown("""
    <style>
    /* Ocultar elementos do Streamlit Cloud para visual profissional */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .viewerBadge_container__1QSob {display: none !important;}
    
    /* Estilo Geral */
    [data-testid="stAppViewContainer"] { background-color: #0e1117; }
    .stButton>button { border-radius: 10px; background-color: #6c5ce7; color: white; width: 100%; font-weight: bold; }
    .product-card { border: 1px solid #333; padding: 20px; border-radius: 15px; background-color: #161b22; }
    h1, h2, h3 { color: #a29bfe; }
    
    /* Botão de Suporte (WhatsApp) no Login */
    .support-btn {
        display: inline-block;
        padding: 10px 20px;
        background-color: transparent;
        color: #25D366;
        border: 2px solid #25D366;
        border-radius: 10px;
        text-decoration: none;
        font-weight: bold;
        text-align: center;
        margin-top: 10px;
        width: 100%;
    }
    .support-btn:hover { background-color: #25D366; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÃO TÉCNICA: VALIDADOR DE CPF ---
def validar_cpf(cpf):
    cpf = re.sub(r'\D', '', cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in range(9, 11):
        value = sum((int(cpf[num]) * ((i + 1) - num) for num in range(0, i)))
        digit = ((value * 10) % 11) % 10
        if digit != int(cpf[i]):
            return False
    return True

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        df = conn.read(ttl=0).dropna(how="all")
        colunas_necessarias = ['nome', 'cor', 'tam', 'tipo', 'novidade', 'preco', 'estoque', 'foto']
        for col in colunas_necessarias:
            if col not in df.columns:
                df[col] = "N/A" if col != 'preco' and col != 'estoque' else 0
        df['preco'] = pd.to_numeric(df['preco'], errors='coerce').fillna(0.0)
        df['estoque'] = pd.to_numeric(df['estoque'], errors='coerce').fillna(0).astype(int)
        for col in ['nome', 'cor', 'tam', 'tipo', 'novidade']:
            df[col] = df[col].astype(str).str.upper().str.strip()
        df['foto'] = df['foto'].astype(str).replace('nan', '').str.strip()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

def salvar(novo_df):
    conn.update(data=novo_df)
    st.cache_data.clear()
    st.rerun()

# --- INICIALIZAÇÃO DE ESTADOS ---
df_estoque = carregar_dados()

if 'cliente_logado' not in st.session_state:
    st.session_state.cliente_logado = False
if 'nome_cliente' not in st.session_state:
    st.session_state.nome_cliente = ""
if 'cpf_cliente' not in st.session_state:
    st.session_state.cpf_cliente = ""
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# --- TELA DE LOGIN ---
if not st.session_state.cliente_logado:
    st.title("👗 Aninha Confecções")
    st.write("Identifique-se para acessar o catálogo:")
    with st.container(border=True):
        nome_input = st.text_input("Nome Completo").upper().strip()
        cpf_input = st.text_input("CPF (apenas números)", max_chars=11)
        if st.button("ACESSAR CATÁLOGO"):
            if len(nome_input) < 5: st.error("Nome muito curto.")
            elif not validar_cpf(cpf_input): st.error("CPF inválido.")
            else:
                st.session_state.nome_cliente, st.session_state.cpf_cliente = nome_input, cpf_input
                st.session_state.cliente_logado = True
                st.rerun()
        
        # Botão de Suporte via WhatsApp (Link direto)
        msg_suporte = urllib.parse.quote("Olá! Estou com dificuldade para acessar o catálogo da loja.")
        # Lembre-se de colocar seu número real abaixo
        link_suporte = f"https://wa.me/5581986707825?text={msg_suporte}"
        st.markdown(f'<a href="{link_suporte}" target="_blank" class="support-btn">💬 Dificuldade no acesso? Fale conosco</a>', unsafe_allow_html=True)
        
    st.stop()

# --- SIDEBAR (APÓS LOGIN) ---
with st.sidebar:
    st.title("𝓐ninha Conf.")
    st.write(f"👤 **{st.session_state.nome_cliente}**")
    if st.button("Sair/Trocar Cliente"):
        st.session_state.cliente_logado = False
        st.rerun()
    st.divider()
    with st.expander("🔐 Admin"):
        senha = st.text_input("Senha", type="password")
        is_admin = (senha == "32500")

# --- LÓGICA DE FILTRO INICIAL ---
tem_novidade = not df_estoque[df_estoque['novidade'] == 'SIM'].empty if not df_estoque.empty else False
if 'filtro_tipo' not in st.session_state:
    st.session_state['filtro_tipo'] = 'NOVIDADES' if tem_novidade else 'TODOS'

# --- VISÃO DO CLIENTE ---
if not is_admin:
    st.header("Catálogo ✨")
    # Filtros por Categorias
    c1, c2, c3, c4, c5 = st.columns(5)
    if c1.button("🏠 TODOS"): st.session_state['filtro_tipo'] = 'TODOS'
    if c2.button("👕 CAMISAS"): st.session_state['filtro_tipo'] = 'CAMISA'
    if c3.button("🩳 BERMUDAS"): st.session_state['filtro_tipo'] = 'BERMUDA'
    if c4.button("👖 CALÇAS"): st.session_state['filtro_tipo'] = 'CALÇA'
    if c5.button("🔥 NOVIDADES"): st.session_state['filtro_tipo'] = 'NOVIDADES'
    
    filtro_atual = st.session_state['filtro_tipo']
    
    if filtro_atual == 'TODOS': df_exibir = df_estoque
    elif filtro_atual == 'NOVIDADES': df_exibir = df_estoque[df_estoque['novidade'] == 'SIM']
    else: df_exibir = df_estoque[df_estoque['tipo'] == filtro_atual]

    busca = st.text_input("🔍 Pesquisar modelo...", "").upper()
    if busca and not df_exibir.empty:
        df_exibir = df_exibir[df_exibir['nome'].str.contains(busca, na=False)]

    if df_exibir is None or df_exibir.empty:
        st.warning(f"Sem itens em '{filtro_atual}'.")
    else:
        col_loja, col_carrinho = st.columns([2, 1])
        with col_loja:
            for nome_p in df_exibir['nome'].unique():
                variantes_prod = df_exibir[df_exibir['nome'] == nome_p]
                with st.container(border=True):
                    c_img, c_info = st.columns([1, 1])
                    with c_info:
                        st.subheader(nome_p)
                        cor_sel = st.selectbox(f"Cor:", variantes_prod['cor'].unique(), key=f"c_{nome_p}")
                        variantes_cor = variantes_prod[variantes_prod['cor'] == cor_sel]
                        tam_sel = st.selectbox(f"Tamanho:", variantes_cor['tam'].unique(), key=f"t_{nome_p}_{cor_sel}")
                        item = variantes_cor[variantes_cor['tam'] == tam_sel].iloc[0]
                        st.write(f"💰 **R$ {float(item['preco']):.2f}**")
                        if int(item['estoque']) > 0:
                            qtd = st.number_input("Qtd:", 1, int(item['estoque']), 1, key=f"q_{item['id']}")
                            if st.button(f"🛒 Adicionar", key=f"b_{item['id']}"):
                                st.session_state.carrinho.append({"nome": nome_p, "cor": cor_sel, "tam": tam_sel, "preco": float(item['preco']), "qtd": qtd})
                                st.toast("Adicionado!")
                        else: st.error("Esgotado")
                    with c_img:
                        if item['foto']: st.image(item['foto'], use_container_width=True)

        with col_carrinho:
