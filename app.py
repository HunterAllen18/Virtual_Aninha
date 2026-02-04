import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Aninha Confecções - Loja Virtual", layout="wide")

# Estilização CSS para um visual moderno e limpo
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0e1117; }
    .stButton>button { border-radius: 10px; background-color: #6c5ce7; color: white; width: 100%; font-weight: bold; }
    .product-card {
        border: 1px solid #333; padding: 20px; border-radius: 15px;
        background-color: #161b22; margin-bottom: 25px;
    }
    h1, h2, h3 { color: #a29bfe; }
    /* Esconde legendas de ajuda para manter o estoque oculto */
    div[data-testid="stMarkdownContainer"] > p { font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        # Lê a planilha em tempo real
        df = conn.read(ttl=0).dropna(how="all")
        
        # Limpeza e padronização dos dados (Correção do Erro 'Series' object has no attribute 'strip')
        df['preco'] = pd.to_numeric(df['preco'], errors='coerce').fillna(0.0)
        df['estoque'] = pd.to_numeric(df['estoque'], errors='coerce').fillna(0).astype(int)
        
        # O segredo é usar .str.strip() em vez de apenas .strip()
        df['nome'] = df['nome'].astype(str).str.upper().str.strip()
        df['cor'] = df['cor'].astype(str).str.upper().str.strip()
        df['tam'] = df['tam'].astype(str).str.upper().str.strip()
        
        df['foto'] = df['foto'].astype(str).replace('nan', '').str.strip()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame(columns=["id", "nome", "cor", "preco", "estoque", "tam", "foto"])

def salvar(novo_df):
    try:
        conn.update(data=novo_df)
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

# --- ESTADO DA SESSÃO ---
df_estoque = carregar_dados()

if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("𝓐ninha Conf.")
    nome_user = st.text_input("Seu Nome para o Pedido", "").upper()
    st.divider()
    with st.expander("🔐 Área do Administrador"):
        senha = st.text_input("Senha", type="password")
        is_admin = (senha == "32500")

# --- LÓGICA DE EXIBIÇÃO ---

if not is_admin:
    # --- VISÃO DO CLIENTE ---
    st.header(f"Olá, {nome_user if nome_user else 'seja bem-vinda(o)'}! ✨")
    busca = st.text_input("🔍 O que você procura?", placeholder="Ex: Camisa, Bermuda...").upper()

    if df_estoque.empty:
        st.info("Catálogo em atualização. Volte logo!")
    else:
        # Filtro de busca por nome
        df_f = df_estoque[df_estoque['nome'].str.contains(busca, na=False)]
        
        col_loja, col_carrinho = st.columns([2, 1])

        with col_loja:
            # Agrupa variantes pelo nome do produto
            for nome_p in df_f['nome'].unique():
                variantes_prod = df_f[df_f['nome'] == nome_p]
                
                with st.container(border=True):
                    c_img, c_info = st.columns([1, 1])
                    
                    with c_info:
                        st.subheader(nome_p)
                        
                        # 1. Escolha da Cor
                        cores_avai = variantes_prod['cor'].unique()
                        cor_sel = st.selectbox(f"Cor:", cores_avai, key=f"c_{nome_p}")
                        
                        # 2. Escolha do Tamanho (Filtrado pela Cor selecionada)
                        variantes_cor = variantes_prod[variantes_prod['cor'] == cor_sel]
                        tams_avai = variantes_cor['tam'].unique()
                        tam_sel = st.selectbox(f"Tamanho:", tams_avai, key=f"t_{nome_p}_{cor_sel}")
                        
                        # Dados finais do item
                        item_final = variantes_cor[variantes_cor['tam'] == tam_sel].iloc[0]
                        estoque_final = int(item_final['estoque'])
                        
                        st.write(f"💰 **R$ {float(item_final['preco']):.2f}**")
                        
                        if estoque_final > 0:
                            # O max_value trava a quantidade, mas o cliente não vê o total disponível
                            qtd = st.number_input("Quantidade:", min_value=1, max_value=estoque_final, value=1, step=1, key=f"q_{item_final['id']}")
                            
                            if st.button(f"🛒 Adicionar", key=f"b_{item_final['id']}"):
                                st.session_state.carrinho.append({
                                    "nome": nome_p, "cor": cor_sel, "tam": tam_sel, 
                                    "preco": float(item_final['preco']), "qtd": qtd
                                })
                                st.toast(f"Adicionado!")
                        else:
                            st.error("Esgotado")

                    with c_img:
                        if item_final['foto'] and item_final['foto'].startswith('http'):
                            st.image(item_final['foto'], use_container_width=True)
                        else:
                            st.write("📦 Foto indisponível")

        with col_carrinho:
            st.subheader("🛒 Carrinho")
            total_geral = 0
            if not st.session_state.carrinho:
                st.write("Vazio")
            else:
                for i, item in enumerate(st.session_state.carrinho):
                    sub = item['preco'] * item['qtd']
                    total_geral += sub
                    c1, c2 = st.columns([4, 1])
                    c1.write(f"**{item['qtd']}x {item['nome']}**\n{item['cor']} | {item['tam']}\nR$ {sub:.2f}")
                    if c2.button("🗑️", key=f"rm_{i}"):
                        st.session_state.carrinho.pop(i)
                        st.rerun()
                
                st.divider()
                st.write(f"### Total: R$ {total_geral:.2f}")
                
                if st.button("🚀 FINALIZAR NO WHATSAPP"):
                    if nome_user:
                        resumo = ""
                        for it in st.session_state.carrinho:
                            resumo += f"- {it['qtd']}x {it['nome']} ({it['cor']} - {it['tam']}) | R$ {it['preco']*it['qtd']:.2f}\n"
                        
                        msg = f"*NOVO PEDIDO - ANINHA CONFECÇÕES*\n👤 Cliente: {nome_user}\n\n*Produtos:*\n{resumo}\n*TOTAL: R$ {total_geral:.2f}*"
                        # Lembre-se de trocar o número abaixo pelo seu
                        link = f"https://wa.me/5581986707825?text={urllib.parse.quote(msg)}"
                        st.markdown(f'<a href="{link}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:15px; border-radius:10px; cursor:pointer; font-weight:bold;">ENVIAR PARA WHATSAPP</button></a>', unsafe_allow_html=True)
                    else:
                        st.warning("⚠️ Digite seu nome na lateral para enviar!")

else:
    # --- PAINEL DO ADMINISTRADOR ---
    st.title("⚙️ Painel de Gestão")
    t_estoque, t_novo = st.tabs(["📦 Estoque Atual", "➕ Cadastrar Item"])
    
    with t_estoque:
        st.write("Visão detalhada (Estoque visível apenas para você)")
        for idx, row in df_estoque.iterrows():
            with st.container(border=True):
                col_info, col_del = st.columns([4, 1])
                col_info.write(f"**{row['nome']}** | {row['cor']} | Tam: {row['tam']}")
                col_info.caption(f"Preço: R$ {row['preco']} | Estoque: {row['estoque']}")
                if col_del.button("Excluir", key=f"del_{idx}"):
                    salvar(df_estoque.drop(idx))
    
    with t_novo:
        with st.form("novo_produto"):
            st.subheader("Cadastrar Novo Produto")
            f_n = st.text_input("Nome do Produto (Ex: Camisa Polo)").upper()
            f_c = st.text_input("Cor (Ex: Rosa)").upper()
            f_t = st.text_input("Tamanho (Ex: M)").upper()
            c1, c2 = st.columns(2)
            f_p = c1.number_input("Preço", min_value=0.0, step=0.01)
            f_e = c2.number_input("Quantidade em Estoque", min_value=0, step=1)
            f_f = st.text_input("Link da Foto")
            
            if st.form_submit_button("Salvar na Planilha"):
                if f_n and f_c and f_t:
                    novo_item = pd.DataFrame([{
                        "id": str(len(df_estoque) + 101),
                        "nome": f_n, "cor": f_c, "tam": f_t,
                        "preco": f_p, "estoque": f_e, "foto": f_f
                    }])
                    salvar(pd.concat([df_estoque, novo_item], ignore_index=True))
                else:
                    st.error("Preencha Nome, Cor e Tamanho!")

