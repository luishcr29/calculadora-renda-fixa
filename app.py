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

# --- Funções auxiliares ---

def formatar_moeda(valor: float) -> str:
    """Formata número como moeda brasileira (R$ 1.234,56)."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def buscar_cdi():
    """
    Busca o CDI diário via API do Banco Central (série SGS 12)
    e converte para taxa anual (% a.a.).
    """
    url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados/ultimos/1?formato=json"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        dados = resp.json()
        valor_str = dados[0]["valor"]
        cdi_diario_pct = float(valor_str.replace(",", "."))
        cdi_diario = cdi_diario_pct / 100.0
        cdi_anual = (1 + cdi_diario) ** 252 - 1
        return cdi_anual * 100  # em %
    except Exception:
        return None

def calcular_prazo_em_dias(start_date, end_date):
    return (end_date - start_date).days

def obter_aliquota_ir(prazo_dias):
    if prazo_dias <= 180:
        return 0.225
    elif prazo_dias <= 360:
        return 0.20
    elif prazo_dias <= 720:
        return 0.175
    else:
        return 0.15

def aliquota_iof(dias):
    """Tabela regressiva IOF (0 a 30 dias)."""
    if dias >= 30:
        return 0.0
    return (30 - dias) / 30

def calcular_rendimento(valor_investido, taxa_anual_percent, prazo_dias):
    taxa_anual = taxa_anual_percent / 100.0
    taxa_diaria = (1 + taxa_anual) ** (1/365)
    return valor_investido * (taxa_diaria ** prazo_dias)

# def calcular_investimento(data_inicio, data_fim, produto, tipo, valor_investido,
#                           taxa_anual=None, cdi=None, percentual_cdi=None, taxa_custodia=0.0):
#     prazo = calcular_prazo_em_dias(data_inicio, data_fim)
#     tributavel = (produto == "CDB")

#     if tipo == "Pré":
#         taxa_efetiva = taxa_anual or 0.0
#     else:
#         taxa_efetiva = (percentual_cdi or 0.0) / 100 * (cdi or 0.0)

#     bruto = calcular_rendimento(valor_investido, taxa_efetiva, prazo)
#     rendimento = bruto - valor_investido

#     iof = 0.0
#     if tributavel and prazo < 30:
#         iof = rendimento * aliquota_iof(prazo)

#     imposto_ir = 0.0
#     if tributavel:
#         aliquota = obter_aliquota_ir(prazo)
#         imposto_ir = (rendimento - iof) * aliquota

#     custo_custodia = valor_investido * (taxa_custodia/100) * (prazo/365)

#     liquido = bruto - imposto_ir - iof - custo_custodia
#     rent_liq_pct = (liquido/valor_investido - 1) * 100 if valor_investido > 0 else 0
#     rent_anual_pct = ((1 + rent_liq_pct/100) ** (365/prazo) - 1) * 100 if prazo > 0 else 0

#     return {
#         "produto": produto,
#         "tipo": tipo,
#         "taxa": taxa_efetiva,
#         "prazo": prazo,
#         "valor_investido": valor_investido,
#         "valor_bruto": bruto,
#         "iof": iof,
#         "imposto_ir": imposto_ir,
#         "custodia": custo_custodia,
#         "valor_liquido": liquido,
#         "rentabilidade": rent_liq_pct,
#         "rentabilidade_anual": rent_anual_pct
#     }

def calcular_rendimento_variavel(valor_investido, taxa_inicial, taxa_final, prazo_dias):
    """
    Calcula o rendimento acumulado considerando que a taxa anual varia
    linearmente da taxa_inicial até a taxa_final ao longo do prazo.
    """
    fator_acumulado = 1.0
    
    # Se o prazo for 0, não há rendimento
    if prazo_dias <= 0:
        return valor_investido

    # Iteramos dia a dia para aplicar a taxa correspondente àquele dia na curva linear
    for dia in range(prazo_dias):
        # Interpolação linear da taxa anual para o dia atual
        # No dia 0 é a taxa inicial, no último dia aproxima-se da taxa final
        taxa_anual_dia = taxa_inicial + (taxa_final - taxa_inicial) * (dia / prazo_dias)
        
        # Converte a taxa anual do dia para taxa diária (base 365 conforme código original)
        taxa_diaria = (1 + taxa_anual_dia) ** (1/365)
        
        fator_acumulado *= taxa_diaria
        
    return valor_investido * fator_acumulado

def calcular_investimento(data_inicio, data_fim, produto, tipo, valor_investido,
                          taxa_anual=None, cdi=None, cdi_fim=None, percentual_cdi=None, taxa_custodia=0.0):
    prazo = calcular_prazo_em_dias(data_inicio, data_fim)
    tributavel = (produto == "CDB")

    bruto = 0.0
    
    # Lógica de Rentabilidade
    if tipo == "Pré":
        # Cálculo Pré-fixado (Mantém lógica original de taxa constante)
        taxa_efetiva = (taxa_anual or 0.0) / 100.0
        taxa_diaria = (1 + taxa_efetiva) ** (1/365)
        bruto = valor_investido * (taxa_diaria ** prazo)
        taxa_media_exibicao = taxa_efetiva # Para fins de registro
        
    else: # Pós-fixado
        pct_cdi = (percentual_cdi or 0.0) / 100.0
        cdi_i = (cdi or 0.0) / 100.0
        
        # Se houver previsão de CDI final e for diferente do inicial
        if cdi_fim is not None:
            cdi_f = cdi_fim / 100.0
            # A taxa efetiva aplicada varia dia a dia: (%CDI * CDI_do_dia)
            taxa_inicial_efetiva = cdi_i * pct_cdi
            taxa_final_efetiva = cdi_f * pct_cdi
            
            bruto = calcular_rendimento_variavel(valor_investido, taxa_inicial_efetiva, taxa_final_efetiva, prazo)
            taxa_media_exibicao = (taxa_inicial_efetiva + taxa_final_efetiva) / 2 # Apenas aproximado para retorno
        else:
            # Cálculo Pós-fixado Clássico (CDI Constante)
            taxa_efetiva = pct_cdi * cdi_i
            taxa_diaria = (1 + taxa_efetiva) ** (1/365)
            bruto = valor_investido * (taxa_diaria ** prazo)
            taxa_media_exibicao = taxa_efetiva

    rendimento = bruto - valor_investido

    # --- Cálculo de Impostos (Mantido igual) ---
    iof = 0.0
    if tributavel and prazo < 30:
        iof = rendimento * aliquota_iof(prazo)

    imposto_ir = 0.0
    if tributavel:
        aliquota = obter_aliquota_ir(prazo)
        imposto_ir = (rendimento - iof) * aliquota

    custo_custodia = valor_investido * (taxa_custodia/100) * (prazo/365)

    liquido = bruto - imposto_ir - iof - custo_custodia
    rent_liq_pct = (liquido/valor_investido - 1) * 100 if valor_investido > 0 else 0
    rent_anual_pct = ((1 + rent_liq_pct/100) ** (365/prazo) - 1) * 100 if prazo > 0 else 0

    return {
        "produto": produto,
        "tipo": tipo,
        "taxa": taxa_media_exibicao, # Apenas referencial
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

# def gerar_grafico(valor_investido, taxa_anual, prazo, produto, tipo, cdi=None, percentual_cdi=None, taxa_custodia=0.0):
#     dias = list(range(1, prazo + 1))
#     valores_liq = []
#     for d in dias:
#         parcial = calcular_investimento(
#             date.today(), date.today() + timedelta(days=d), produto, tipo, valor_investido,
#             taxa_anual=taxa_anual, cdi=cdi, percentual_cdi=percentual_cdi, taxa_custodia=taxa_custodia
#         )
#         valores_liq.append(parcial["valor_liquido"])
#     fig, ax = plt.subplots(figsize=(7, 4))
#     ax.plot(dias, valores_liq, label="Valor Líquido")
#     ax.set_title("Evolução do Investimento")
#     ax.set_xlabel("Dias")
#     ax.set_ylabel("Valor (R$)")
#     ax.legend()
#     return fig

# Atualizar a função gerar_grafico para aceitar cdi_fim
def gerar_grafico(valor_investido, taxa_anual, prazo, produto, tipo, cdi=None, cdi_fim=None, percentual_cdi=None, taxa_custodia=0.0):
    dias = list(range(1, prazo + 1))
    valores_liq = []
    
    # Para o gráfico ficar correto na projeção, assumimos que a 'curva' de juros 
    # se move conforme o tempo passa até o prazo final original.
    
    for d in dias:
        # Nota: Ao calcular dias parciais, a lógica linear assume que se você sacar antes,
        # o CDI variou proporcionalmente até aquele dia.
        
        # Se o CDI final for definido, calculamos qual seria o CDI 'final' para este sub-prazo 'd'
        # ou mantemos a lógica de que a curva de juros é fixa no tempo. 
        # Para simplificar a visualização: passamos o cdi_fim original. 
        # A função calcular_investimento fará a interpolação interna de 0 até 'd'.
        
        # Ajuste fino: Se a previsão é 12% em 365 dias, no dia 180 a taxa momentânea é ~12.8%.
        # Se passarmos cdi_fim=12 e prazo=180 para a função, ela vai achar que a taxa cai para 12 em 180 dias (queda mais brusca).
        # Correção da projeção para o gráfico:
        cdi_fim_ajustado = cdi_fim
        if cdi_fim is not None and cdi is not None and prazo > 0:
            # O CDI alvo no dia 'd' segue a reta original
            cdi_fim_ajustado = cdi + (cdi_fim - cdi) * (d / prazo)

        parcial = calcular_investimento(
            date.today(), date.today() + timedelta(days=d), produto, tipo, valor_investido,
            taxa_anual=taxa_anual, cdi=cdi, cdi_fim=cdi_fim_ajustado, percentual_cdi=percentual_cdi, taxa_custodia=taxa_custodia
        )
        valores_liq.append(parcial["valor_liquido"])
        
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(dias, valores_liq, label="Valor Líquido")
    ax.set_title("Evolução do Investimento")
    ax.set_xlabel("Dias")
    ax.set_ylabel("Valor (R$)")
    ax.legend()
    return fig

# --- Interface Streamlit ---

st.title("📈 Calculadora de Rendimento — Renda Fixa")
st.write("Calcule e compare CDB, LCI e LCA, considerando IR, IOF e taxa de custódia.")

cdi_auto = buscar_cdi()
if cdi_auto:
    st.info(f"📊 CDI atual (BCB): **{cdi_auto:.2f}%** ao ano")
else:
    st.warning("⚠️ Não foi possível buscar o CDI automaticamente. Insira o valor manualmente.")

# --- Seção de Inputs ---
with st.expander("💰 Configurações do Investimento", expanded=True):
    comparar = st.checkbox("Comparar dois investimentos?")

    # def render_inputs(prefix):
    #     st.subheader(prefix)
    #     col1, col2 = st.columns(2)
    #     with col1:
    #         data_inicio = st.date_input("📆 Data início", value=date.today(), key=prefix+"_start")
    #         data_fim = st.date_input("🗓️ Data fim", value=date.today()+timedelta(days=365), key=prefix+"_end")
    #         produto = st.selectbox("🛍️ Produto", ("CDB","LCI","LCA"), key=prefix+"_produto")
    #         tipo = st.selectbox("⚙️ Tipo de rendimento", ("Pré","Pós"), key=prefix+"_tipo")
    #     with col2:
    #         valor_investido = st.number_input("💵 Valor investido (R$)", min_value=100.0, value=1000.0, step=100.0, key=prefix+"_valor")
    #         taxa_custodia = st.number_input("📉 Taxa de custódia (% ao ano)", min_value=0.0, value=0.0, step=0.1, format="%.2f", key=prefix+"_custodia")
    #         taxa_anual = None
    #         cdi = None
    #         percentual_cdi = None
    #         if tipo == "Pré":
    #             taxa_anual = st.number_input("Taxa anual (%)", value=10.0, step=1.0, key=prefix+"_taxa")
    #         else:
    #             cdi = cdi_auto or st.number_input("CDI anual atual (%)", value=13.65, step=0.1, format="%.2f", key=prefix+"_cdi")
    #             percentual_cdi = st.number_input("Percentual do CDI (%)", value=100.0, step=1.0, key=prefix+"_pcdi")
        
    #     # Validação de datas
    #     if data_fim <= data_inicio:
    #         st.error("A data de fim deve ser posterior à data de início.")
    #         return None, None, None, None, None, None, None, None, None
        
    #     return data_inicio, data_fim, produto, tipo, valor_investido, taxa_anual, cdi, percentual_cdi, taxa_custodia

    # Atualizar a função render_inputs para incluir a variavel cdi_fim
    def render_inputs(prefix):
        st.subheader(prefix)
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("📆 Data início", value=date.today(), key=prefix+"_start")
            data_fim = st.date_input("🗓️ Data fim", value=date.today()+timedelta(days=365), key=prefix+"_end")
            produto = st.selectbox("🛍️ Produto", ("CDB","LCI","LCA"), key=prefix+"_produto")
            tipo = st.selectbox("⚙️ Tipo de rendimento", ("Pré","Pós"), key=prefix+"_tipo")
        with col2:
            valor_investido = st.number_input("💵 Valor investido (R$)", min_value=100.0, value=1000.0, step=100.0, key=prefix+"_valor")
            taxa_custodia = st.number_input("📉 Taxa de custódia (% ao ano)", min_value=0.0, value=0.0, step=0.1, format="%.2f", key=prefix+"_custodia")
            
            taxa_anual = None
            cdi = None
            cdi_fim = None # Nova variável
            percentual_cdi = None
            
            if tipo == "Pré":
                taxa_anual = st.number_input("Taxa anual (%)", value=10.0, step=1.0, key=prefix+"_taxa")
            else:
                cdi = cdi_auto or st.number_input("CDI anual atual (%)", value=13.65, step=0.1, format="%.2f", key=prefix+"_cdi")
                
                # Checkbox para habilitar projeção
                usar_projecao = st.checkbox("Considerar previsão futura do CDI?", key=prefix+"_check_proj")
                if usar_projecao:
                    cdi_fim = st.number_input("CDI previsto no final (%)", value=cdi, step=0.1, format="%.2f", key=prefix+"_cdi_fim")
                
                percentual_cdi = st.number_input("Percentual do CDI (%)", value=100.0, step=1.0, key=prefix+"_pcdi")
        
        if data_fim <= data_inicio:
            st.error("A data de fim deve ser posterior à data de início.")
            # Retornamos None extra para manter consistência
            return None, None, None, None, None, None, None, None, None, None 
        
        # Retorna também o cdi_fim
        return data_inicio, data_fim, produto, tipo, valor_investido, taxa_anual, cdi, cdi_fim, percentual_cdi, taxa_custodia
    
    # Execução principal e exibição dos resultados
    if comparar:
        col1, col2 = st.columns(2)
        with col1:
            p1 = render_inputs("Investimento 1")
        with col2:
            p2 = render_inputs("Investimento 2")

        # Verifica se p1 e p2 não são None (lembrando que agora retornam 10 itens)
        if p1 and p2 and p1[0] is not None: 
            inv1 = calcular_investimento(*p1)
            inv2 = calcular_investimento(*p2)
        
        # if p1 and p2:
        #     inv1 = calcular_investimento(*p1)
        #     inv2 = calcular_investimento(*p2)
            
            with st.expander("📊 Comparativo dos Investimentos", expanded=True):
                df = pd.DataFrame([inv1, inv2])
                df_fmt = df.rename(columns={
                    "produto": "Produto",
                    "prazo": "Prazo (dias)",
                    "valor_investido": "Valor Investido",
                    "valor_liquido": "Valor Líquido",
                    "rentabilidade_anual": "Rentabilidade Anual (%)"
                })
                df_exibicao = df_fmt[["Produto", "Prazo (dias)", "Valor Investido", "Valor Líquido", "Rentabilidade Anual (%)"]].copy()
                df_exibicao["Valor Investido"] = df_exibicao["Valor Investido"].apply(formatar_moeda)
                df_exibicao["Valor Líquido"] = df_exibicao["Valor Líquido"].apply(formatar_moeda)
                df_exibicao["Rentabilidade Anual (%)"] = df_exibicao["Rentabilidade Anual (%)"].apply(lambda x: f"{x:.2f}%")
                
                st.dataframe(df_exibicao, hide_index=True, use_container_width=True)
                melhor = "Investimento 1" if inv1["rentabilidade_anual"] > inv2["rentabilidade_anual"] else "Investimento 2"
                st.success(f"🏆 **O melhor investimento é: {melhor}**")
        else:
            st.warning("⚠️ Preencha os campos de ambos os investimentos para comparar.")

    else:
        p = render_inputs("Investimento")
        
        # if p:
        #     inv = calcular_investimento(*p)

        if p and p[0] is not None:
            inv = calcular_investimento(*p)
            
            st.markdown("---")
            st.subheader("🎯 Resultado do seu Investimento")
            
            col_principal, col_secundaria = st.columns(2)
            
            with col_principal:
                st.metric(
                    label="💰 Valor Líquido Final",
                    value=formatar_moeda(inv['valor_liquido']),
                    delta=f"Ganho: {formatar_moeda(inv['valor_liquido'] - inv['valor_investido'])}"
                )
                
                st.metric(
                    label="📊 Rentabilidade Líquida Total",
                    value=f"{inv['rentabilidade']:.2f}%"
                )
                
                st.metric(
                    label="📈 Rentabilidade Anualizada",
                    value=f"{inv['rentabilidade_anual']:.2f}%"
                )
            
            # with col_secundaria:
            #     fig = gerar_grafico(inv['valor_investido'], p[5], inv['prazo'], inv['produto'], inv['tipo'], p[6], p[7], p[8])
            #     st.pyplot(fig)

            with col_secundaria:
                # Atualize a chamada do gráfico passando os índices corretos
                # p[0]=inicio, p[1]=fim, p[2]=prod, p[3]=tipo, p[4]=valor, 
                # p[5]=taxa_anual, p[6]=cdi, p[7]=cdi_fim, p[8]=perc_cdi, p[9]=custodia
                fig = gerar_grafico(
                    inv['valor_investido'], p[5], inv['prazo'], inv['produto'], 
                    inv['tipo'], cdi=p[6], cdi_fim=p[7], percentual_cdi=p[8], taxa_custodia=p[9]
                )
                st.pyplot(fig)
            
            with st.expander("🧾 Detalhes da Tributação e Custos"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Prazo:** {inv['prazo']} dias")
                    st.write(f"**Valor Investido:** {formatar_moeda(inv['valor_investido'])}")
                    st.write(f"**Valor Bruto:** {formatar_moeda(inv['valor_bruto'])}")
                with col2:
                    st.write(f"**Imposto de Renda (IR):** {formatar_moeda(inv['imposto_ir'])}")
                    st.write(f"**Imposto sobre Operações Financeiras (IOF):** {formatar_moeda(inv['iof'])}")
                    st.write(f"**Taxa de Custódia:** {formatar_moeda(inv['custodia'])}")

