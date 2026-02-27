import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Aninha Confecções - Vitrine", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0e1117; }
    .stButton>button { border-radius: 10px; background-color: #6c5ce7; color: white; width: 100%; font-weight: bold; }
    .product-card { border: 1px solid #333; padding: 20px; border-radius: 15px; background-color: #161b22; }
    h1, h2, h3 { color: #a29bfe; }
    /* Ajuste para ícones de categoria */
    .stHorizontalBlock { gap: 10px; }
    </style>
    """, unsafe_allow_html=True)
st.markdown("""
    <style>
    /* Esconder o menu superior direito (ícone do GitHub e links) */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Remove o botão 'Made with Streamlit' e o link do GitHub */
    .viewerBadge_container__1QSob {display: none !important;}
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        df = conn.read(ttl=0).dropna(how="all")
        
        # Garantir colunas essenciais
        colunas_necessarias = ['nome', 'cor', 'tam', 'tipo', 'novidade', 'preco', 'estoque', 'foto']
        for col in colunas_necessarias:
            if col not in df.columns:
                df[col] = "N/A" if col != 'preco' and col != 'estoque' else 0

        # Tratamento numérico
        df['preco'] = pd.to_numeric(df['preco'], errors='coerce').fillna(0.0)
        df['estoque'] = pd.to_numeric(df['estoque'], errors='coerce').fillna(0).astype(int)
        
        # Tratamento de texto (Removendo espaços e padronizando)
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

# --- CARREGAMENTO E LÓGICA DE FILTRO INICIAL ---
df_estoque = carregar_dados()

# Verifica se há novidades antes de definir o filtro inicial
tem_novidade = not df_estoque[df_estoque['novidade'] == 'SIM'].empty

if 'filtro_tipo' not in st.session_state:
    st.session_state['filtro_tipo'] = 'NOVIDADES' if tem_novidade else 'TODOS'

if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# --- SIDEBAR ---
with st.sidebar:
    st.title("𝓐ninha Conf.")
    nome_user = st.text_input("Seu Nome", "").upper()
    st.divider()
    with st.expander("🔐 Administrador"):
        senha = st.text_input("Senha", type="password")
        is_admin = (senha == "32500")

# --- VISÃO DO CLIENTE ---
if not is_admin:
    st.header(f"Olá, {nome_user if nome_user else 'visitante'}! ✨")
    
    # --- FILTROS POR ÍCONES ---
    st.write("### Categorias")
    c1, c2, c3, c4, c5 = st.columns(5)
    
    if c1.button("🏠 TODOS"): st.session_state['filtro_tipo'] = 'TODOS'
    if c2.button("👕 CAMISAS"): st.session_state['filtro_tipo'] = 'CAMISA'
    if c3.button("🩳 BERMUDAS"): st.session_state['filtro_tipo'] = 'BERMUDA'
    if c4.button("👖 CALÇAS"): st.session_state['filtro_tipo'] = 'CALÇA'
    if c5.button("🔥 NOVIDADES"): st.session_state['filtro_tipo'] = 'NOVIDADES'
    
    filtro_atual = st.session_state['filtro_tipo']
    st.info(f"Mostrando: **{filtro_atual}**")
    
    # Aplicação do Filtro
    if filtro_atual == 'TODOS':
        df_exibir = df_estoque
    elif filtro_atual == 'NOVIDADES':
        df_exibir = df_estoque[df_estoque['novidade'] == 'SIM']
    else:
        df_exibir = df_estoque[df_estoque['tipo'] == filtro_atual]

    busca = st.text_input("🔍 Pesquisar peça específica...", "").upper()
    if busca:
        df_exibir = df_exibir[df_exibir['nome'].str.contains(busca, na=False)]

    # --- VITRINE ---
    if df_exibir.empty:
        st.warning(f"Sem itens em '{filtro_atual}' no momento.")
    else:
        col_loja, col_carrinho = st.columns([2, 1])

        with col_loja:
            for nome_p in df_exibir['nome'].unique():
                variantes_prod = df_exibir[df_exibir['nome'] == nome_p]
                with st.container(border=True):
                    c_img, c_info = st.columns([1, 1])
                    with c_info:
                        st.subheader(nome_p)
                        
                        # Seletor de Cor
                        cor_sel = st.selectbox(f"Cor:", variantes_prod['cor'].unique(), key=f"c_{nome_p}")
                        
                        # Seletor de Tamanho (Filtrado pela cor)
                        variantes_cor = variantes_prod[variantes_prod['cor'] == cor_sel]
                        tam_sel = st.selectbox(f"Tamanho:", variantes_cor['tam'].unique(), key=f"t_{nome_p}_{cor_sel}")
                        
                        # Item final e trava de estoque
                        item = variantes_cor[variantes_cor['tam'] == tam_sel].iloc[0]
                        st.write(f"💰 **R$ {float(item['preco']):.2f}**")
                        
                        estoque_limite = int(item['estoque'])
                        if estoque_limite > 0:
                            qtd = st.number_input("Qtd:", 1, estoque_limite, 1, key=f"q_{item['id']}")
                            if st.button(f"🛒 Adicionar", key=f"b_{item['id']}"):
                                st.session_state.carrinho.append({
                                    "nome": nome_p, "cor": cor_sel, "tam": tam_sel, 
                                    "preco": float(item['preco']), "qtd": qtd
                                })
                                st.toast("Adicionado!")
                        else:
                            st.error("Esgotado")
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
                st.divider()
                st.write(f"### Total: R$ {total:.2f}")
                if st.button("🚀 FINALIZAR PEDIDO") and nome_user:
                    resumo = "\n".join([f"- {it['qtd']}x {it['nome']} ({it['cor']}-{it['tam']})" for it in st.session_state.carrinho])
                    msg = f"*NOVO PEDIDO - ANINHA CONFECÇÕES*\n👤 Cliente: {nome_user}\n\n*Produtos:*\n{resumo}\n\n*Total: R$ {total:.2f}*"
                    link = f"https://wa.me/5581986707825?text={urllib.parse.quote(msg)}"
                    st.markdown(f'<a href="{link}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:15px; border-radius:10px; font-weight:bold; width:100%; cursor:pointer;">ENVIAR PARA WHATSAPP</button></a>', unsafe_allow_html=True)
                elif not nome_user:
                    st.warning("Informe seu nome na barra lateral!")

else:
    # --- PAINEL ADMIN ---
    st.title("⚙️ Gestão de Estoque")
    t1, t2 = st.tabs(["📦 Estoque Atual", "➕ Adicionar Produto"])
    with t1:
        for idx, row in df_estoque.iterrows():
            with st.container(border=True):
                st.write(f"**{row['nome']}** | {row['tipo']} | Novidade: {row['novidade']} | Estoque: **{row['estoque']}**")
                if st.button("Excluir", key=f"del_{idx}"): salvar(df_estoque.drop(idx))
    with t2:
        with st.form("add_prod"):
            f_n = st.text_input("Nome do Modelo").upper()
            c_a, c_b = st.columns(2)
            f_tipo = c_a.selectbox("Tipo", ["CAMISA", "BERMUDA", "CALÇA", "OUTROS"])
            f_nov = c_b.selectbox("É Novidade?", ["NÃO", "SIM"])
            f_c = st.text_input("Cor").upper()
            f_t = st.text_input("Tamanho").upper()
            f_p = st.number_input("Preço")
            f_e = st.number_input("Quantidade", step=1)
            f_f = st.text_input("Link da Foto")
            if st.form_submit_button("💾 Salvar"):
                novo = pd.DataFrame([{"id": str(len(df_estoque)+101), "nome": f_n, "tipo": f_tipo, "novidade": f_nov, "cor": f_c, "tam": f_t, "preco": f_p, "estoque": f_e, "foto": f_f}])
                salvar(pd.concat([df_estoque, novo], ignore_index=True))


