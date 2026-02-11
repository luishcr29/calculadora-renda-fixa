# app.py
from datetime import date, timedelta
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
import locale

st.set_page_config(page_title="Calculadora Renda Fixa", layout="wide")

# Definir locale para formato monetário (Brasil)
try:
    locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
except:
    locale.setlocale(locale.LC_ALL, "")

# --- Constantes ---
PRODUTOS_ISENTOS = ["LCI", "LCA", "CRI", "CRA", "Debênture Incentivada"]

# --- Funções de API (Com Cache) ---

@st.cache_data(ttl=3600)
def buscar_cdi():
    """Busca o CDI atual no Banco Central."""
    url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados/ultimos/1?formato=json"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        dados = resp.json()
        valor_str = dados[0]["valor"]
        cdi_diario = float(valor_str.replace(",", ".")) / 100.0
        return ((1 + cdi_diario) ** 252 - 1) * 100
    except Exception:
        return None

@st.cache_data(ttl=3600)
def buscar_ipca_focus():
    """Busca a expectativa de IPCA (Focus)."""
    url = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoInflacao12Meses?$top=1&$orderby=Data desc&$filter=Indicador eq 'IPCA'"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if "value" in data and len(data["value"]) > 0:
            return data["value"][0]["Mediana"]
        return None
    except Exception:
        return None

# --- Funções de Cálculo ---

def calcular_prazo_em_dias(start_date, end_date):
    return (end_date - start_date).days

def obter_aliquota_ir(prazo_dias):
    if prazo_dias <= 180: return 0.225
    elif prazo_dias <= 360: return 0.20
    elif prazo_dias <= 720: return 0.175
    else: return 0.15

def aliquota_iof(dias):
    if dias >= 30: return 0.0
    return (30 - dias) / 30

def calcular_rendimento(valor_investido, taxa_anual_percent, prazo_dias):
    """Cálculo padrão para taxa constante."""
    taxa_anual = taxa_anual_percent / 100.0
    taxa_diaria = (1 + taxa_anual) ** (1/365)
    return valor_investido * (taxa_diaria ** prazo_dias)

def calcular_rendimento_variavel(valor_investido, taxa_inicial, taxa_final, prazo_dias):
    """
    Calcula o rendimento com taxa variável (interpolação linear).
    Útil para CDI que começa em X% e termina em Y%.
    """
    if prazo_dias <= 0: return valor_investido
    
    fator_acumulado = 1.0
    # Itera dia a dia para compor a taxa que muda diariamente
    for dia in range(prazo_dias):
        # Taxa do dia específico (interpolação linear)
        taxa_momento = taxa_inicial + (taxa_final - taxa_inicial) * (dia / prazo_dias)
        
        # Converte para base diária (365 dias)
        taxa_diaria = (1 + taxa_momento/100.0) ** (1/365)
        fator_acumulado *= taxa_diaria
        
    return valor_investido * fator_acumulado

def calcular_investimento(data_inicio, data_fim, produto, tipo, valor_investido,
                          taxa_anual=None, cdi=None, cdi_fim=None, percentual_cdi=None, 
                          ipca_projetado=None, taxa_fixa_ipca=None, taxa_custodia=0.0):
    
    prazo = calcular_prazo_em_dias(data_inicio, data_fim)
    
    # Isenção
    isento = produto in PRODUTOS_ISENTOS
    tributavel = not isento

    # Cálculo do Bruto
    bruto = 0.0
    taxa_exibicao = 0.0 # Para mostrar na tela (média ou efetiva)
    
    if tipo == "Pré":
        taxa_exibicao = taxa_anual or 0.0
        bruto = calcular_rendimento(valor_investido, taxa_exibicao, prazo)
        
    elif tipo == "Pós (CDI)":
        pct_cdi = (percentual_cdi or 0.0) / 100.0
        val_cdi_ini = (cdi or 0.0)
        
        # Verifica se existe projeção de CDI final
        if cdi_fim is not None:
            val_cdi_fim = cdi_fim
            
            # As taxas efetivas aplicadas são (%CDI * CDI_do_Momento)
            taxa_efetiva_ini = val_cdi_ini * pct_cdi
            taxa_efetiva_fim = val_cdi_fim * pct_cdi
            
            bruto = calcular_rendimento_variavel(valor_investido, taxa_efetiva_ini, taxa_efetiva_fim, prazo)
            
            # Taxa média apenas para referência visual
            taxa_exibicao = (taxa_efetiva_ini + taxa_efetiva_fim) / 2
        else:
            # Cálculo Padrão (CDI constante)
            taxa_exibicao = val_cdi_ini * pct_cdi
            bruto = calcular_rendimento(valor_investido, taxa_exibicao, prazo)
        
    elif tipo == "IPCA +":
        idx_ipca = (ipca_projetado or 0.0) / 100
        idx_fixa = (taxa_fixa_ipca or 0.0) / 100
        taxa_combinada = ((1 + idx_ipca) * (1 + idx_fixa) - 1) * 100
        taxa_exibicao = taxa_combinada
        bruto = calcular_rendimento(valor_investido, taxa_exibicao, prazo)

    rendimento = bruto - valor_investido

    # Tributação
    iof = 0.0
    if tributavel and prazo < 30:
        iof = rendimento * aliquota_iof(prazo)

    imposto_ir = 0.0
    if tributavel:
        aliquota = obter_aliquota_ir(prazo)
        imposto_ir = (rendimento - iof) * aliquota

    # Custos
    custo_custodia = valor_investido * (taxa_custodia/100) * (prazo/365)

    liquido = bruto - imposto_ir - iof - custo_custodia
    rent_liq_pct = (liquido/valor_investido - 1) * 100 if valor_investido > 0 else 0
    rent_anual_pct = ((1 + rent_liq_pct/100) ** (365/prazo) - 1) * 100 if prazo > 0 else 0

    return {
        "produto": produto,
        "tipo": tipo,
        "taxa": taxa_exibicao,
        "prazo": prazo,
        "valor_investido": valor_investido,
        "valor_bruto": bruto,
        "iof": iof,
        "imposto_ir": imposto_ir,
        "custodia": custo_custodia,
        "valor_liquido": liquido,
        "rentabilidade": rent_liq_pct,
        "rentabilidade_anual": rent_anual_pct
    }

def gerar_grafico(valor_investido, prazo, taxa_inicial, taxa_final=None):
    """
    Gera gráfico da evolução. Se taxa_final for fornecida, faz interpolação.
    """
    dias = list(range(1, prazo + 1))
    valores = []
    
    saldo = valor_investido
    
    # Se for taxa fixa (ou CDI constante)
    if taxa_final is None or taxa_final == taxa_inicial:
        taxa_diaria = (1 + taxa_inicial/100) ** (1/365)
        for _ in dias:
            saldo *= taxa_diaria
            valores.append(saldo)
    else:
        # Taxa variável
        for d in range(prazo):
            # Recalcula a taxa do dia específico
            taxa_momento = taxa_inicial + (taxa_final - taxa_inicial) * (d / prazo)
            taxa_diaria = (1 + taxa_momento/100) ** (1/365)
            saldo *= taxa_diaria
            valores.append(saldo)
            
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(dias, valores, label="Evolução Bruta")
    ax.set_title("Crescimento do Patrimônio (Bruto)")
    ax.set_xlabel("Dias")
    ax.set_ylabel("Valor (R$)")
    ax.legend()
    return fig

def formatar_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- Interface Streamlit ---

st.title("📈 Calculadora de Rendimento — Renda Fixa")
st.write("Calcule e compare CDB, LCI, LCA, CRI, CRA e Debêntures.")

# --- Indicadores ---
col_inds1, col_inds2 = st.columns(2)
with col_inds1:
    cdi_auto = buscar_cdi()
    if cdi_auto:
        st.info(f"📊 **CDI Atual (BCB):** {cdi_auto:.2f}% ao ano")
    else:
        st.warning("⚠️ CDI: API indisponível (usando valor padrão).")

with col_inds2:
    ipca_auto = buscar_ipca_focus()
    if ipca_auto:
        st.success(f"🏷️ **IPCA Projetado (Focus 12m):** {ipca_auto:.2f}%")
    else:
        st.caption("⚠️ API Focus instável. Usando IPCA padrão de mercado.")

# --- Inputs ---
with st.expander("💰 Configurações do Investimento", expanded=True):
    comparar = st.checkbox("Comparar dois investimentos?")

    def render_inputs(prefix):
        st.subheader(prefix)
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("📆 Data início", value=date.today(), key=prefix+"_start")
            data_fim = st.date_input("🗓️ Data fim", value=date.today()+timedelta(days=365), key=prefix+"_end")
            
            lista_produtos = ("CDB", "LCI", "LCA", "CRI", "CRA", "Debênture Simples", "Debênture Incentivada")
            produto = st.selectbox("🛍️ Produto", lista_produtos, key=prefix+"_produto")
            tipo = st.selectbox("⚙️ Tipo de rendimento", ("Pré", "Pós (CDI)", "IPCA +"), key=prefix+"_tipo")
        
        with col2:
            valor_investido = st.number_input("💵 Valor investido (R$)", min_value=100.0, value=1000.0, step=100.0, key=prefix+"_valor")
            taxa_custodia = st.number_input("📉 Taxa de custódia (% ao ano)", min_value=0.0, value=0.0, step=0.1, format="%.2f", key=prefix+"_custodia")
            
            taxa_anual = None
            cdi = None
            cdi_fim = None # Variável para projeção
            percentual_cdi = None
            ipca_projetado = None
            taxa_fixa_ipca = None

            if tipo == "Pré":
                taxa_anual = st.number_input("Taxa pré-fixada (% a.a.)", value=12.0, step=0.5, key=prefix+"_taxa")
            
            elif tipo == "Pós (CDI)":
                val_cdi = cdi_auto if cdi_auto else 13.0
                cdi = st.number_input("CDI anual atual (% a.a.)", value=val_cdi, step=0.1, format="%.2f", key=prefix+"_cdi")
                
                # Checkbox de Projeção
                usar_projecao = st.checkbox("Projetar CDI futuro?", key=prefix+"_projecao")
                if usar_projecao:
                    cdi_fim = st.number_input("CDI previsto no final (% a.a.)", value=cdi, step=0.1, format="%.2f", key=prefix+"_cdi_fim")
                
                percentual_cdi = st.number_input("Percentual do CDI (%)", value=100.0, step=1.0, key=prefix+"_pcdi")
            
            elif tipo == "IPCA +":
                c_ipca1, c_ipca2 = st.columns(2)
                with c_ipca1:
                    taxa_fixa_ipca = st.number_input("Taxa Fixa (IPCA + ?)", value=6.0, step=0.5, format="%.2f", key=prefix+"_taxafixa")
                with c_ipca2:
                    val_ipca = ipca_auto if ipca_auto else 4.50
                    ipca_projetado = st.number_input("IPCA projetado (% a.a.)", value=val_ipca, step=0.1, format="%.2f", key=prefix+"_ipca")

        if data_fim <= data_inicio:
            st.error("A data de fim deve ser posterior à data de início.")
            return None
        
        return {
            "data_inicio": data_inicio, "data_fim": data_fim, "produto": produto, "tipo": tipo,
            "valor_investido": valor_investido, "taxa_anual": taxa_anual, 
            "cdi": cdi, "cdi_fim": cdi_fim, "percentual_cdi": percentual_cdi,
            "ipca_projetado": ipca_projetado, "taxa_fixa_ipca": taxa_fixa_ipca,
            "taxa_custodia": taxa_custodia
        }

    p1_params = None
    p2_params = None

    if comparar:
        col1, col2 = st.columns(2)
        with col1: p1_params = render_inputs("Investimento 1")
        with col2: p2_params = render_inputs("Investimento 2")
    else:
        p1_params = render_inputs("Investimento")

    if p1_params:
        inv1 = calcular_investimento(**p1_params)
        inv2 = None
        if comparar and p2_params:
            inv2 = calcular_investimento(**p2_params)

        if comparar and inv2:
            st.markdown("---")
            with st.expander("📊 Comparativo Detalhado", expanded=True):
                df = pd.DataFrame([inv1, inv2])
                df_fmt = df.copy()
                
                cols_moeda = ["valor_investido", "valor_bruto", "valor_liquido", "imposto_ir", "iof", "custodia"]
                for col in cols_moeda:
                    df_fmt[col] = df_fmt[col].apply(formatar_moeda)
                
                df_fmt["taxa"] = df_fmt["taxa"].apply(lambda x: f"{x:.2f}%")
                df_fmt["rentabilidade_anual"] = df_fmt["rentabilidade_anual"].apply(lambda x: f"{x:.2f}%")
                
                cols_finais = {
                    "produto": "Produto", "tipo": "Tipo", "taxa": "Taxa Média/Efetiva",
                    "prazo": "Prazo (dias)", "valor_liquido": "Valor Líquido",
                    "rentabilidade_anual": "Rentabilidade Anual"
                }
                st.dataframe(df_fmt[cols_finais.keys()].rename(columns=cols_finais), hide_index=True, use_container_width=True)

                melhor = "Investimento 1" if inv1["rentabilidade_anual"] > inv2["rentabilidade_anual"] else "Investimento 2"
                st.success(f"🏆 **O melhor investimento é: {melhor}**")
        
        else:
            st.markdown("---")
            st.subheader("🎯 Resultado do Investimento")
            
            col_main, col_graph = st.columns([1, 1])
            
            with col_main:
                st.metric(
                    label="Valor Líquido Final",
                    value=formatar_moeda(inv1['valor_liquido']),
                    delta=f"Lucro Líquido: {formatar_moeda(inv1['valor_liquido'] - inv1['valor_investido'])}"
                )
                
                st.write("") 
                
                # Exibição das métricas
                label_taxa = "Taxa Média (Estimada)" if inv1.get('cdi_fim_usado') else "Taxa Efetiva (Nominal)"
                st.metric(label_taxa, f"{inv1['taxa']:.2f}% a.a.")
                st.metric("Rentabilidade Realizada", f"{inv1['rentabilidade']:.2f}%")
                st.metric("Rentabilidade Anualizada", f"{inv1['rentabilidade_anual']:.2f}%")
            
            with col_graph:
                # Prepara os dados para o gráfico (considerando se houve projeção ou não)
                taxa_ini_graph = inv1['taxa']
                taxa_fim_graph = None
                
                # Se for Pós (CDI) com projeção, precisamos recalcular as taxas para o gráfico
                if inv1['tipo'] == "Pós (CDI)" and p1_params.get('cdi_fim'):
                     pct = (p1_params['percentual_cdi'] or 0)/100
                     taxa_ini_graph = (p1_params['cdi'] or 0) * pct
                     taxa_fim_graph = (p1_params['cdi_fim'] or 0) * pct
                
                fig = gerar_grafico(inv1['valor_investido'], inv1['prazo'], taxa_ini_graph, taxa_fim_graph)
                st.pyplot(fig)
            
            with st.expander("🧾 Extrato Detalhado"):
                c1, c2, c3 = st.columns(3)
                c1.write(f"**Investido:** {formatar_moeda(inv1['valor_investido'])}")
                c1.write(f"**Bruto:** {formatar_moeda(inv1['valor_bruto'])}")
                
                c2.write(f"**IR Estimado:** {formatar_moeda(inv1['imposto_ir'])}")
                c2.write(f"**IOF:** {formatar_moeda(inv1['iof'])}")
                
                c3.write(f"**Custódia:** {formatar_moeda(inv1['custodia'])}")
                c3.write(f"**Líquido:** {formatar_moeda(inv1['valor_liquido'])}")

            if inv1['produto'] in PRODUTOS_ISENTOS:
                st.info(f"ℹ️ O produto **{inv1['produto']}** é isento de IR para Pessoa Física.")
