import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Aninha Confecções - Loja Virtual", layout="wide")

# Estilização para Mobile e Desktop
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child {
        background-color: #6c5ce7;
        color: white;
        border-radius: 10px;
        width: 100%;
    }
    .delete-btn button {
        background-color: #ff4b4b !important;
        color: white !important;
    }
    .product-card {
        border: 1px solid #333;
        padding: 15px;
        border-radius: 15px;
        background-color: #161b22;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM GOOGLE SHEETS ---
# Certifique-se de configurar o link da planilha no Secrets do Streamlit Cloud
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        # ttl=0 garante que os dados não fiquem em cache antigo ao atualizar
        df = conn.read(ttl=0)
        return df.dropna(how="all")
    except:
        # Se a planilha estiver vazia ou não configurada, retorna estrutura base
        return pd.DataFrame(columns=["id", "nome", "preco", "estoque", "cores", "tam", "foto"])

def salvar_mudancas(novo_df):
    conn.update(data=novo_df)
    st.cache_data.clear()
    st.rerun()

# --- CARGA INICIAL ---
df_estoque = carregar_dados()

if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# --- SIDEBAR: CLIENTE E ADMIN ---
with st.sidebar:
    st.title("𝓐ninha Conf.")
    nome_user = st.text_input("Seu Nome (para o pedido)", "").upper()
    
    st.divider()
    with st.expander("🔐 Área do Lojista"):
        senha = st.text_input("Senha", type="password")
        is_admin = (senha == "32500")

# --- TELA PRINCIPAL ---
if not is_admin:
    # --- VISÃO DO CLIENTE ---
    st.header(f"Olá, {nome_user if nome_user else 'bem-vinda(o)'}! ✨")
    busca = st.text_input("🔍 O que você procura hoje?", placeholder="Digite o nome de uma peça...").upper()

    col_vitrine, col_pedido = st.columns([2, 1])

    with col_vitrine:
        # Filtrar produtos pelo nome (busca parecida)
        if not df_estoque.empty:
            prods = df_estoque[df_estoque['nome'].astype(str).str.contains(busca, na=False)]
        else:
            prods = pd.DataFrame()

        if prods.empty:
            st.info("Nenhum produto encontrado no catálogo no momento.")
        else:
            # Exibir em Grade (2 colunas no mobile/web)
            for i in range(0, len(prods), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(prods):
                        p = prods.iloc[i + j]
                        with cols[j]:
                            st.markdown('<div class="product-card">', unsafe_allow_html=True)
                            if p['foto']:
                                st.image(p['foto'], use_container_width=True)
                            else:
                                st.write("📦 Sem foto")
                            
                            st.subheader(p['nome'])
                            st.write(f"**R$ {p['preco']:.2f}**")
                            st.caption(f"Tamanhos: {p['tam']} | Cores: {p['cores']}")
                            
                            disp = "✅ Disponível" if p['estoque'] > 0 else "❌ Esgotado"
                            st.write(disp)
                            
                            if p['estoque'] > 0:
                                if st.button(f"🛒 Adicionar", key=f"add_{p['id']}"):
                                    st.session_state.carrinho.append(p.to_dict())
                                    st.toast("Adicionado!")
                            st.markdown('</div>', unsafe_allow_html=True)

    with col_pedido:
        st.subheader("🛒 Meu Carrinho")
        if not st.session_state.carrinho:
            st.write("Vazio")
        else:
            total_pedido = 0
            for idx, item in enumerate(st.session_state.carrinho):
                c_c1, c_c2 = st.columns([4, 1])
                c_c1.write(f"**{item['nome']}**\nR$ {item['preco']:.2f}")
                if c_c2.button("🗑️", key=f"rem_{idx}"):
                    st.session_state.carrinho.pop(idx)
                    st.rerun()
                total_pedido += item['preco']
            
            st.divider()
            st.write(f"### Total: R$ {total_pedido:.2f}")
            
            if st.button("🚀 Enviar p/ WhatsApp", use_container_width=True):
                if nome_user:
                    msg = f"*PEDIDO ANINHA CONFECÇÕES*\n\n👤 Cliente: {nome_user}\n"
                    for it in st.session_state.carrinho:
                        msg += f"- {it['nome']} (R$ {it['preco']:.2f})\n"
                    msg += f"\n*TOTAL: R$ {total_pedido:.2f}*"
                    
                    link_zap = f"https://wa.me/5581985595236?text={urllib.parse.quote(msg)}"
                    st.markdown(f'<a href="{link_zap}" target="_blank">CONFIRMAR NO WHATSAPP</a>', unsafe_allow_html=True)
                else:
                    st.error("Digite seu nome na barra lateral para finalizar!")

else:
    # --- VISÃO DO ADMINISTRADOR ---
    st.title("⚙️ Painel Administrativo")
    
    t1, t2 = st.tabs(["📦 Gerenciar Produtos", "➕ Cadastrar Novo"])
    
    with t1:
        st.subheader("Produtos Cadastrados")
        if df_estoque.empty:
            st.info("Sua planilha está vazia.")
        else:
            for index, row in df_estoque.iterrows():
                with st.container(border=True):
                    col_det, col_acao = st.columns([4, 1])
                    with col_det:
                        st.write(f"**{row['nome']}**")
                        st.caption(f"Preço: R$ {row['preco']} | Estoque: {row['estoque']} | ID: {row['id']}")
                    with col_acao:
                        st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
                        if st.button("🗑️ Remover", key=f"del_{row['id']}"):
                            novo_df = df_estoque.drop(index)
                            salvar_mudancas(novo_df)
                            st.success("Removido!")
                        st.markdown('</div>', unsafe_allow_html=True)

    with t2:
        st.subheader("Nova Peça")
        with st.form("form_add", clear_on_submit=True):
            f_nome = st.text_input("Nome do Produto").upper()
            c1, c2 = st.columns(2)
            f_preco = c1.number_input("Preço", min_value=0.0)
            f_est = c2.number_input("Qtd Estoque", min_value=0)
            f_tam = st.text_input("Tamanhos (ex: P, M, G)")
            f_cores = st.text_input("Cores")
            f_foto = st.text_input("Link da Foto (Imgur/PostImages)")
            
            if st.form_submit_button("💾 Salvar na Nuvem"):
                if f_nome:
                    novo_id = str(len(df_estoque) + 101) # Gera ID simples
                    novo_item = pd.DataFrame([{
                        "id": novo_id, "nome": f_nome, "preco": f_preco,
                        "estoque": f_est, "cores": f_cores, "tam": f_tam, "foto": f_foto
                    }])
                    df_final = pd.concat([df_estoque, novo_item], ignore_index=True)
                    salvar_mudancas(df_final)
                    st.success("Cadastrado com sucesso!")
                else:
                    st.error("O nome é obrigatório.")

