import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import re

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Aninha Confecções", layout="wide")

# CSS para Customização e Ocultação Total
st.markdown("""
    <style>
    /* 1. Esconde barra superior, menu, rodapé e logo do Streamlit */
    header, #MainMenu, footer, .stAppDeployButton, [data-testid="stStatusWidget"], .viewerBadge_container__1QSob {
        display: none !important;
    }
    
    /* Estilo Geral da Loja */
    [data-testid="stAppViewContainer"] { background-color: #0e1117; color: white; }
    .stButton>button { border-radius: 10px; background-color: #6c5ce7; color: white; width: 100%; font-weight: bold; }
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
    
    /* Esconder o label do expander discreto */
    .st-emotion-cache-1644v4k {display: none;}
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
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# --- TELA DE LOGIN ---
if not st.session_state.cliente_logado and not st.session_state.is_admin:
    st.title("Aninha Confecções")
    st.write("Identifique-se para acessar o catálogo:")
    with st.container(border=True):
        nome_input = st.text_input("Nome Completo").upper().strip()
        cpf_input = st.text_input("CPF (apenas números)", max_chars=11)
        if st.button("ACESSAR CATÁLOGO"):
            if len(nome_input) < 5: st.error("Nome inválido.")
            elif not validar_cpf(cpf_input): st.error("CPF inválido.")
            else:
                st.session_state.nome_cliente, st.session_state.cpf_cliente = nome_input, cpf_input
                st.session_state.cliente_logado = True
                st.rerun()
        
        # Botão de Suporte (Link direto)
        msg_suporte = urllib.parse.quote("Olá! Estou com dificuldade para acessar o catálogo da loja.")
        link_suporte = f"https://wa.me/5581985595236?text={msg_suporte}"
        st.markdown(f'<a href="{link_suporte}" target="_blank" class="support-btn">💬 Dificuldade? Fale conosco</a>', unsafe_allow_html=True)
        
    st.stop()

# --- LÓGICA DE FILTRO INICIAL (CLIENTE) ---
if 'filtro_tipo' not in st.session_state:
    st.session_state['filtro_tipo'] = 'TODOS'

# --- VITRINE / PAINEL ADMIN ---
if st.session_state.is_admin:
    st.title("⚙️ Painel do Administrador")
    t1, t2 = st.tabs(["📦 Estoque", "➕ Novo"])
    with t1:
        for idx, row in df_estoque.iterrows():
            with st.container(border=True):
                st.write(f"**{row['nome']}** | {row['tipo']} | Estoque: {row['estoque']}")
                if st.button("Excluir", key=f"del_{idx}"): salvar(df_estoque.drop(idx))
    with t2:
        with st.form("add"):
            f_n = st.text_input("Nome").upper()
            f_tipo = st.selectbox("Tipo", ["CAMISA", "BERMUDA", "CALÇA", "OUTROS"])
            f_nov = st.selectbox("Novidade?", ["NÃO", "SIM"])
            f_c, f_t = st.text_input("Cor").upper(), st.text_input("Tamanho").upper()
            f_p, f_e = st.number_input("Preço"), st.number_input("Qtd", step=1)
            f_f = st.text_input("Link Foto")
            if st.form_submit_button("Salvar"):
                novo = pd.DataFrame([{"id": str(len(df_estoque)+101), "nome": f_n, "tipo": f_tipo, "novidade": f_nov, "cor": f_c, "tam": f_t, "preco": f_p, "estoque": f_e, "foto": f_f}])
                salvar(pd.concat([df_estoque, novo], ignore_index=True))
    
    if st.button("🔓 Sair do Modo Admin"):
        st.session_state.is_admin = False
        st.session_state.cliente_logado = False
        st.rerun()
else:
    # --- VISÃO DO CLIENTE (VITRINE) ---
    st.header(f"Olá, {st.session_state.nome_cliente.split()[0]}! ✨")
    
    df_exibir = df_estoque

    # --- VITRINE ---
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
        st.subheader("🛒 Carrinho")
        total = sum(i['preco'] * i['qtd'] for i in st.session_state.carrinho)
        for i, item in enumerate(st.session_state.carrinho):
            c_item, c_del = st.columns([4, 1])
            c_item.write(f"**{item['qtd']}x {item['nome']}**\n{item['cor']} | {item['tam']}")
            if c_del.button("🗑️", key=f"rm_{i}"):
                st.session_state.carrinho.pop(i)
                st.rerun()
        if st.session_state.carrinho:
            st.write(f"### Total: R$ {total:.2f}")
            if st.button("🚀 FINALIZAR"):
                resumo = "\n".join([f"- {it['qtd']}x {it['nome']} ({it['cor']}-{it['tam']})" for it in st.session_state.carrinho])
                msg = f"*NOVO PEDIDO!!!*\n👤 Cliente: {st.session_state.nome_cliente}\n🆔 CPF: {st.session_state.cpf_cliente}\n\n*Produtos:*\n{resumo}\n\n*Total: R$ {total:.2f}*"
                link = f"https://wa.me/5581986707825?text={urllib.parse.quote(msg)}"
                st.markdown(f'<a href="{link}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:15px; border-radius:10px; font-weight:bold; width:100%; cursor:pointer;">ENVIAR PARA WHATSAPP</button></a>', unsafe_allow_html=True)

# --- RODAPÉ DISCRETO (SEM SIDEBAR) ---
st.markdown("---")
col1, col2, col3 = st.columns([1, 1, 1])
with col3:
    with st.expander("."):
        senha_input = st.text_input("Senha Admin", type="password")
        if senha_input == "1234":
            st.session_state.is_admin = True
            st.rerun() # Atualiza instantaneamente ao acertar a senha
