import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Aninha Confecções - Catálogo", layout="wide")

# Estilos CSS para uma aparência profissional e moderna
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0e1117; }
    .stButton>button { border-radius: 10px; background-color: #6c5ce7; color: white; width: 100%; }
    .stButton>button:hover { background-color: #a29bfe; color: white; }
    .product-card {
        border: 1px solid #333;
        padding: 20px;
        border-radius: 15px;
        background-color: #161b22;
        margin-bottom: 25px;
    }
    .delete-btn button { background-color: #ff4b4b !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        # ttl=0 força a atualização sempre que a página for recarregada
        df = conn.read(ttl=0)
        return df.dropna(how="all")
    except:
        return pd.DataFrame(columns=["id", "nome", "cor", "preco", "estoque", "tam", "foto"])

def salvar_mudancas(novo_df):
    conn.update(data=novo_df)
    st.cache_data.clear()
    st.rerun()

# --- CARREAR DADOS ---
df_estoque = carregar_dados()

if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# --- SIDEBAR: IDENTIFICAÇÃO E ADMIN ---
with st.sidebar:
    st.title("𝓐ninha Conf.")
    nome_cliente = st.text_input("Seu Nome (para o pedido)", "").upper()
    
    st.divider()
    with st.expander("🔐 Painel do Lojista"):
        senha = st.text_input("Senha Admin", type="password")
        is_admin = (senha == "1234")

# --- LÓGICA DA INTERFACE ---

if not is_admin:
    # --- VISÃO DO CLIENTE ---
    st.header(f"Bem-vinda(o), {nome_cliente if nome_cliente else 'visitante'}! ✨")
    busca = st.text_input("🔍 O que deseja procurar?", placeholder="Ex: Camisa, Bermuda...").upper()

    if df_estoque.empty:
        st.info("O catálogo está a ser preparado. Volte em breve!")
    else:
        # Filtro de busca
        df_filtrado = df_estoque[df_estoque['nome'].astype(str).str.contains(busca, na=False)]
        
        # Agrupar variantes pelo nome do produto
        nomes_produtos = df_filtrado['nome'].unique()
        
        col_vitrine, col_carrinho = st.columns([2, 1])

        with col_vitrine:
            for nome_p in nomes_produtos:
                # Todas as cores deste modelo
                variantes = df_filtrado[df_filtrado['nome'] == nome_p]
                
                with st.container(border=True):
                    c_img, c_info = st.columns([1, 1])
                    
                    with c_info:
                        st.subheader(nome_p)
                        
                        # Seletor de Cores
                        cores_disponiveis = variantes['cor'].tolist()
                        cor_selecionada = st.selectbox(f"Cor:", cores_disponiveis, key=f"sel_{nome_p}")
                        
                        # Dados específicos da cor escolhida
                        dados_cor = variantes[variantes['cor'] == cor_selecionada].iloc[0]
                        
                        st.write(f"💰 **R$ {dados_cor['preco']:.2f}**")
                        st.caption(f"Tamanhos: {dados_cor['tam']}")
                        
                        # Status de Stock (Ocultando quantidade exata)
                        status = "✅ Disponível" if dados_cor['estoque'] > 0 else "❌ Esgotado"
                        st.write(status)
                        
                        if dados_cor['estoque'] > 0:
                            if st.button(f"🛒 Adicionar ao Carrinho", key=f"btn_{dados_cor['id']}"):
                                item_cart = {
                                    "nome": f"{nome_p} ({cor_selecionada})",
                                    "preco": dados_cor['preco']
                                }
                                st.session_state.carrinho.append(item_cart)
                                st.toast(f"{nome_p} adicionado!")

                    with c_img:
                        # A FOTO MUDA AQUI CONFORME A COR ESCOLHIDA
                        if dados_cor['foto']:
                            st.image(dados_cor['foto'], use_container_width=True)
                        else:
                            st.write("📦 Sem foto disponível")

        with col_carrinho:
            st.subheader("🛒 Meu Carrinho")
            if not st.session_state.carrinho:
                st.write("O seu carrinho está vazio.")
            else:
                total_cart = 0
                for i, item in enumerate(st.session_state.carrinho):
                    c_item1, c_item2 = st.columns([4, 1])
                    c_item1.write(f"**{item['nome']}**\nR$ {item['preco']:.2f}")
                    if c_item2.button("❌", key=f"rem_{i}"):
                        st.session_state.carrinho.pop(i)
                        st.rerun()
                    total_cart += item['preco']
                
                st.divider()
                st.write(f"### Total: R$ {total_cart:.2f}")
                
                if st.button("✅ FINALIZAR PEDIDO"):
                    if nome_cliente:
                        msg = f"*NOVO PEDIDO - ANINHA CONFECÇÕES*\n👤 Cliente: {nome_cliente}\n\n"
                        for it in st.session_state.carrinho:
                            msg += f"- {it['nome']} (R$ {it['preco']:.2f})\n"
                        msg += f"\n*TOTAL: R$ {total_cart:.2f}*"
                        link_zap = f"https://wa.me/5581986707825?text={urllib.parse.quote(msg)}"
                        st.markdown(f'<a href="{link_zap}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:10px; border-radius:10px; cursor:pointer;">ABRIR WHATSAPP</button></a>', unsafe_allow_html=True)
                    else:
                        st.error("Por favor, digite o seu nome na barra lateral.")

else:
    # --- VISÃO DO ADMINISTRADOR ---
    st.title("⚙️ Painel Administrativo")
    
    t_lista, t_novo = st.tabs(["📦 Gerenciar Stock", "➕ Novo Produto"])
    
    with t_lista:
        if df_estoque.empty:
            st.write("Nenhum produto na base de dados.")
        else:
            for index, row in df_estoque.iterrows():
                with st.container(border=True):
                    col_txt, col_del = st.columns([4, 1])
                    with col_txt:
                        st.write(f"**{row['nome']} - {row['cor']}**")
                        st.caption(f"Preço: {row['preco']} | Stock: {row['estoque']} | ID: {row['id']}")
                    with col_del:
                        st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
                        if st.button("🗑️", key=f"del_{row['id']}"):
                            novo_df = df_estoque.drop(index)
                            salvar_mudancas(novo_df)
                        st.markdown('</div>', unsafe_allow_html=True)

    with t_novo:
        st.subheader("Cadastrar Variante (Cor)")
        with st.form("add_form", clear_on_submit=True):
            f_nome = st.text_input("Nome do Modelo (Ex: Blusa Laço)").upper()
            f_cor = st.text_input("Cor (Ex: Rosa Bebê)").upper()
            c1, c2 = st.columns(2)
            f_preco = c1.number_input("Preço", min_value=0.0, step=1.0)
            f_est = c2.number_input("Stock", min_value=0, step=1)
            f_tam = st.text_input("Tamanhos (Ex: P, M, G)")
            f_foto = st.text_input("Link Direto da Foto (JPG/PNG)")
            
            if st.form_submit_button("💾 Salvar na Planilha"):
                if f_nome and f_cor:
                    novo_id = str(len(df_estoque) + 101)
                    item_novo = pd.DataFrame([{
                        "id": novo_id, "nome": f_nome, "cor": f_cor,
                        "preco": f_preco, "estoque": f_est,
                        "tam": f_tam, "foto": f_foto
                    }])
                    df_final = pd.concat([df_estoque, item_novo], ignore_index=True)
                    salvar_mudancas(df_final)
                    st.success("Cadastrado!")
                else:
                    st.error("Preencha o nome e a cor!")

