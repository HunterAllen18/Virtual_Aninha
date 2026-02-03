import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Aninha Confecções - Loja Virtual", layout="wide")

# Estilização para uma vitrine moderna e profissional
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0e1117; }
    .stButton>button { border-radius: 10px; background-color: #6c5ce7; color: white; width: 100%; font-weight: bold; }
    .product-card {
        border: 1px solid #333; padding: 20px; border-radius: 15px;
        background-color: #161b22; margin-bottom: 25px;
    }
    .delete-btn button { background-color: #ff4b4b !important; color: white !important; }
    h1, h2, h3 { color: #a29bfe; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM GOOGLE SHEETS (USANDO SECRETS JSON) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        # Lê os dados em tempo real (ttl=0)
        df = conn.read(ttl=0).dropna(how="all")
        
        # Tratamento de segurança para evitar quebras por dados vazios ou mal digitados
        df['preco'] = pd.to_numeric(df['preco'], errors='coerce').fillna(0.0)
        df['estoque'] = pd.to_numeric(df['estoque'], errors='coerce').fillna(0).astype(int)
        df['nome'] = df['nome'].astype(str).replace('nan', 'PRODUTO SEM NOME').str.upper()
        df['cor'] = df['cor'].astype(str).replace('nan', 'PADRÃO').str.upper()
        df['tam'] = df['tam'].astype(str).replace('nan', 'ÚNICO').str.upper()
        df['foto'] = df['foto'].astype(str).replace('nan', '')
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha: {e}")
        return pd.DataFrame(columns=["id", "nome", "cor", "preco", "estoque", "tam", "foto"])

def salvar(novo_df):
    try:
        conn.update(data=novo_df)
        st.cache_data.clear()
        st.success("Dados atualizados com sucesso!")
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao salvar na planilha: {e}")

# Carregar o banco de dados
df_estoque = carregar_dados()

# Inicializar o carrinho na memória do navegador
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.title("𝓐ninha Conf.")
    nome_user = st.text_input("Seu Nome para o Pedido", "").upper()
    st.divider()
    with st.expander("🔐 Área do Administrador"):
        senha = st.text_input("Senha de Acesso", type="password")
        is_admin = (senha == "32500")

# --- LÓGICA PRINCIPAL: CLIENTE VS ADMIN ---

if not is_admin:
    # --- VISÃO DO CLIENTE ---
    st.header(f"Seja bem-vinda(o), {nome_user if nome_user else 'visitante'}! ✨")
    busca = st.text_input("🔍 O que você procura hoje?", placeholder="Camisa, Bermuda...").upper()

    if df_estoque.empty:
        st.info("O catálogo está vazio no momento. Volte mais tarde!")
    else:
        # Filtro de busca
        df_f = df_estoque[df_estoque['nome'].str.contains(busca, na=False)]
        
        col_loja, col_carrinho = st.columns([2, 1])

        with col_loja:
            # Agrupa produtos repetidos para mostrar apenas uma vez com seletor de cores
            for nome_p in df_f['nome'].unique():
                variantes = df_f[df_f['nome'] == nome_p]
                
                with st.container(border=True):
                    c_img, c_info = st.columns([1, 1])
                    
                    with c_info:
                        st.subheader(nome_p)
                        
                        # Seletor de Cores
                        cores_disponiveis = variantes['cor'].unique()
                        cor_sel = st.selectbox(f"Selecione a Cor:", cores_disponiveis, key=f"s_{nome_p}")
                        
                        # Pega os dados específicos da cor selecionada
                        item = variantes[variantes['cor'] == cor_sel].iloc[0]
                        estoque_real = int(item['estoque'])
                        
                        st.write(f"💰 **R$ {float(item['preco']):.2f}**")
                        st.write(f"📏 Tamanhos: **{item['tam']}**")
                        
                        # Só permite compra se houver estoque
                        if estoque_real > 0:
                            # O limite 'max_value' trava a compra no estoque disponível, mas o valor total fica oculto
                            qtd = st.number_input("Quantidade:", min_value=1, max_value=estoque_real, value=1, key=f"q_{item['id']}")
                            
                            if st.button(f"🛒 Adicionar ao Carrinho", key=f"b_{item['id']}"):
                                st.session_state.carrinho.append({
                                    "nome": nome_p, 
                                    "cor": cor_sel, 
                                    "tam": item['tam'], 
                                    "preco": float(item['preco']),
                                    "qtd": qtd
                                })
                                st.toast(f"{qtd}x {nome_p} ({cor_sel}) adicionado!")
                        else:
                            st.error("Infelizmente esta cor esgotou!")

                    with c_img:
                        if item['foto'] and item['foto'].startswith('http'):
                            st.image(item['foto'], use_container_width=True)
                        else:
                            st.write("📦 Foto em breve")

        with col_carrinho:
            st.subheader("🛒 Meu Carrinho")
            total_geral = 0
            if not st.session_state.carrinho:
                st.write("Seu carrinho está vazio.")
            else:
                for i, item in enumerate(st.session_state.carrinho):
                    subtotal = item['preco'] * item['qtd']
                    total_geral += subtotal
                    c1, c2 = st.columns([4, 1])
                    c1.write(f"**{item['qtd']}x {item['nome']}**\n{item['cor']} | Tam: {item['tam']}\nSubtotal: R$ {subtotal:.2f}")
                    if c2.button("🗑️", key=f"rm_{i}"):
                        st.session_state.carrinho.pop(i)
                        st.rerun()
                
                st.divider()
                st.write(f"### Total: R$ {total_geral:.2f}")

                if st.button("🚀 ENVIAR PARA WHATSAPP"):
                    if nome_user:
                        resumo_zap = ""
                        for it in st.session_state.carrinho:
                            sub_it = it['preco'] * it['qtd']
                            resumo_zap += f"- {it['qtd']}x {it['nome']} ({it['cor']}) | Tam: {it['tam']} | R$ {sub_it:.2f}\n"
                        
                        msg_final = f"*PEDIDO - ANINHA CONFECÇÕES*\n👤 Cliente: {nome_user}\n\n*Produtos:*\n{resumo_zap}\n*TOTAL: R$ {total_geral:.2f}*"
                        link_zap = f"https://wa.me/5581986707825?text={urllib.parse.quote(msg_final)}"
                        st.markdown(f'<a href="{link_zap}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:15px; border-radius:10px; cursor:pointer; font-weight:bold;">CONFIRMAR PEDIDO NO WHATSAPP</button></a>', unsafe_allow_html=True)
                    else:
                        st.warning("⚠️ Por favor, digite seu nome na lateral para finalizar!")

else:
    # --- ÁREA DO ADMINISTRADOR ---
    st.title("⚙️ Painel de Controle")
    aba_estoque, aba_novo = st.tabs(["📦 Gerenciar Estoque", "➕ Adicionar Produto"])
    
    with aba_estoque:
        st.write("Aqui você vê o estoque real que está oculto para os clientes.")
        for idx, row in df_estoque.iterrows():
            with st.container(border=True):
                col_txt, col_del = st.columns([4, 1])
                col_txt.write(f"**{row['nome']}** ({row['cor']}) | Tam: {row['tam']}")
                col_txt.caption(f"Preço: R$ {row['preco']} | **Estoque Real: {row['estoque']}**")
                if col_del.button("Excluir", key=f"del_{idx}"):
                    salvar(df_estoque.drop(idx))
    
    with aba_novo:
        st.subheader("Cadastrar Novo Item")
        with st.form("form_admin", clear_on_submit=True):
            f_nome = st.text_input("Nome do Modelo").upper()
            f_cor = st.text_input("Cor").upper()
            c1, c2 = st.columns(2)
            f_preco = c1.number_input("Preço de Venda", min_value=0.0)
            f_estoque = c2.number_input("Quantidade em Estoque", min_value=0, step=1)
            f_tam = st.text_input("Tamanhos (ex: P, M, G, ÚNICO)").upper()
            f_foto = st.text_input("Link da Foto (PostImages/Imgur)")
            
            if st.form_submit_button("💾 Salvar na Planilha"):
                if f_nome and f_cor:
                    novo_prod = pd.DataFrame([{
                        "id": str(len(df_estoque) + 101),
                        "nome": f_nome, "cor": f_cor, "preco": f_preco,
                        "estoque": int(f_estoque), "tam": f_tam, "foto": f_foto
                    }])
                    salvar(pd.concat([df_estoque, novo_prod], ignore_index=True))
                else:
                    st.error("Obrigatório preencher Nome e Cor!")
