import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Aninha Confecções Web", layout="wide", initial_sidebar_state="expanded")

# CSS para deixar com cara de App Profissional
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0e1117; }
    .stButton>button { border-radius: 20px; background-color: #6c5ce7; color: white; border: none; }
    .stButton>button:hover { background-color: #a29bfe; color: white; }
    .product-box { border: 1px solid #333; padding: 15px; border-radius: 15px; background-color: #161b22; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM GOOGLE SHEETS (SIMULADA PARA EXEMPO) ---
# Nota: Para conectar de verdade, você usaria st.connection("gsheets", type=GSheetsConnection)
# Aqui manteremos a lógica de session_state que sincroniza com seu catálogo
if 'estoque' not in st.session_state:
    st.session_state.estoque = {
        "1": {"nome": "VESTIDO FLORAL", "preco": 89.90, "estoque": 5, "cores": "Azul, Rosa", "tam": "P, M", "foto": "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=500"},
        "2": {"nome": "CONJUNTO MOLETOM", "preco": 120.00, "estoque": 3, "cores": "Cinza", "tam": "G", "foto": "https://images.unsplash.com/photo-1556807457-9c4f0a491ca7?w=500"}
    }

if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# --- SIDEBAR: IDENTIFICAÇÃO ---
with st.sidebar:
    st.title("𝓐ninha Conf.")
    st.markdown("---")
    nome = st.text_input("Seu Nome", placeholder="Ex: Maria Silva").upper()
    
    with st.expander("🔐 Painel Admin"):
        senha = st.text_input("Senha", type="password")
        is_admin = senha == "32500"

# --- TELA PRINCIPAL ---
if not is_admin:
    # VISÃO DO CLIENTE
    st.header(f"Olá, {nome if nome else 'bem-vinda(o)'}! 👋")
    busca = st.text_input("🔍 O que você está procurando hoje?", "").upper()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Catálogo")
        # Grade de produtos
        prods = [p for p in st.session_state.estoque.values() if busca in p['nome']]
        
        if not prods:
            st.warning("Nenhum produto encontrado com esse nome.")
        
        # Criando a grade 2x2 para mobile/web
        for i in range(0, len(prods), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(prods):
                    p = prods[i+j]
                    with cols[j]:
                        st.markdown(f'<div class="product-box">', unsafe_allow_html=True)
                        st.image(p['foto'], use_container_width=True)
                        st.subheader(f"{p['nome']}")
                        st.write(f"💰 **R$ {p['preço']:.2f}**")
                        
                        status = "✅ Disponível" if p['estoque'] > 0 else "❌ Esgotado"
                        st.caption(f"Status: {status} | Tam: {p['tam']}")
                        
                        if p['estoque'] > 0:
                            if st.button(f"Adicionar ao Carrinho", key=f"btn_{p['nome']}"):
                                st.session_state.carrinho.append(p)
                                st.toast(f"{p['nome']} adicionado!")
                        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.subheader("🛒 Meu Pedido")
        if not st.session_state.carrinho:
            st.info("Seu carrinho está vazio.")
        else:
            total = 0
            for idx, item in enumerate(st.session_state.carrinho):
                c_item1, c_item2 = st.columns([3, 1])
                c_item1.write(f"**{item['nome']}**\nR$ {item['preco']:.2f}")
                if c_item2.button("❌", key=f"del_{idx}"):
                    st.session_state.carrinho.pop(idx)
                    st.rerun()
                total += item['preco']
            
            st.markdown("---")
            st.write(f"### Total: R$ {total:.2f}")
            
            if st.button("✅ FINALIZAR NO WHATSAPP", use_container_width=True):
                if not nome:
                    st.error("Por favor, digite seu nome na barra lateral!")
                else:
                    itens_msg = ""
                    for i in st.session_state.carrinho:
                        itens_msg += f"- {i['nome']} (R$ {i['preco']:.2f})\n"
                    
                    texto_zap = f"*NOVO PEDIDO - ANINHACONFECÇOES*\n\n👤 *Cliente:* {nome}\n\n*Itens:*\n{itens_msg}\n💰 *TOTAL: R$ {total:.2f}*"
                    link_zap = f"https://wa.me/5581985595236?text={urllib.parse.quote(texto_zap)}"
                    st.markdown(f'<a href="{link_zap}" target="_blank"><button style="width:100%; height:50px; background-color:#25D366; color:white; border:none; border-radius:10px; cursor:pointer; font-weight:bold;">ABRIR WHATSAPP AGORA</button></a>', unsafe_allow_html=True)

else:
    # VISÃO DO ADMINISTRADOR
    st.header("⚙️ Gestão de Loja")
    
    tab1, tab2 = st.tabs(["📦 Ver Estoque", "➕ Adicionar Produto"])
    
    with tab1:
        df_estoque = pd.DataFrame(st.session_state.estoque).T
        st.table(df_estoque[['nome', 'preco', 'estoque', 'tam']])
        if st.button("Limpar Dados (Reset)"):
            st.session_state.estoque = {}
            st.rerun()

    with tab2:
        with st.form("novo_prod"):
            f_nome = st.text_input("Nome do Produto")
            f_preco = st.number_input("Preço", min_value=0.0)
            f_qtd = st.number_input("Estoque", min_value=0)
            f_tam = st.text_input("Tamanhos (ex: P, M, G)")
            f_foto = st.text_input("Link da Foto (URL)")
            
            if st.form_submit_button("Cadastrar Produto"):
                new_id = str(len(st.session_state.estoque) + 1)
                st.session_state.estoque[new_id] = {
                    "nome": f_nome.upper(),
                    "preco": f_preco,
                    "estoque": f_qtd,
                    "tam": f_tam,
                    "foto": f_foto
                }
                st.success("Produto cadastrado com sucesso!")

                st.rerun()

