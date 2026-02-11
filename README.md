Aqui está o texto **corrigido e devidamente formatado em Markdown**, pronto para colar no seu `README.md`:

---

# 💰 Calculadora de Renda Fixa (Brasil)

Uma aplicação web interativa desenvolvida em **Python** e **Streamlit** para simular, comparar e analisar investimentos de **Renda Fixa no Brasil**.

A ferramenta considera as regras tributárias atuais (**Imposto de Renda e IOF**), taxas de custódia e busca indicadores econômicos (**CDI e IPCA**) automaticamente de fontes oficiais do **Banco Central**.

---

## 🚀 Funcionalidades

### 1. Ampla Cobertura de Produtos

Simule rendimentos para os principais ativos do mercado:

* **Tributáveis:** CDB (Certificado de Depósito Bancário) e Debêntures Simples
* **Isentos de IR (Pessoa Física):** LCI, LCA, CRI, CRA e Debêntures Incentivadas

---

### 2. Tipos de Rentabilidade

A calculadora suporta os três principais modelos de remuneração:

* **Pré-fixado:** Taxa fixa anual (ex: 12% a.a.)
* **Pós-fixado (CDI):** Percentual do CDI (ex: 110% do CDI)

  * Inclui funcionalidade de **Projeção de Curva**, permitindo estimar o rendimento caso o CDI suba ou caia durante o período (interpolação linear da taxa)
* **Híbrido (IPCA +):** Inflação + taxa fixa (ex: IPCA + 6%)

---

### 3. Integração com APIs Oficiais 📡

O aplicativo busca dados em tempo real para facilitar a simulação:

* **CDI Atual:** Consulta direta à API do Banco Central (Série SGS)
* **IPCA Projetado:** Consulta as expectativas do mercado (Boletim Focus) para os próximos 12 meses via API Olinda/BCB
* **Fallback Inteligente:** Caso as APIs estejam indisponíveis, o sistema utiliza valores padrão de mercado, permitindo que o usuário continue usando a ferramenta manualmente

---

### 4. Análise Detalhada

* **Comparador:** Coloque dois investimentos lado a lado para ver qual rende mais líquido
* **Gráficos:** Visualização da evolução do patrimônio bruto ao longo do tempo
* **Indicadores:**

  * Taxa Efetiva
  * Rentabilidade Realizada (no período)
  * Rentabilidade Anualizada
* **Tributação Automática:**

  * Cálculo automático da tabela regressiva do IR (22,5% a 15%)
  * Cálculo do IOF para resgates inferiores a 30 dias
  * Destaque automático para produtos isentos

---

## 🛠️ Tecnologias Utilizadas

* [Python 3](https://www.python.org/)
* [Streamlit](https://streamlit.io/) — Interface Web
* [Pandas](https://pandas.pydata.org/) — Manipulação de dados
* [Matplotlib](https://matplotlib.org/) — Visualização gráfica
* [Requests](https://pypi.org/project/requests/) — Consumo de APIs

---

## 📦 Como Rodar o Projeto

### Pré-requisitos

Certifique-se de ter o **Python 3** instalado em sua máquina.

---

### Passo a passo

### 1️⃣ Clone o repositório

```bash
git clone https://github.com/SEU-USUARIO/calculadora-renda-fixa.git
cd calculadora-renda-fixa
```

### 2️⃣ Crie e ative um ambiente virtual (recomendado)

#### Windows

```bash
python -m venv venv
.\venv\Scripts\activate
```

#### Linux / Mac

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Instale as dependências

```bash
pip install -r requirements.txt
```

### 4️⃣ Execute a aplicação

```bash
streamlit run app.py
```

### 5️⃣ Acesse

O navegador abrirá automaticamente em:

```
http://localhost:8501
```

---

## 🧮 Lógica de Cálculo

* **Base de Dias:** capitalização diária exponencial (base 365 dias corridos) para converter taxas anuais em diárias
* **Projeção de CDI:** interpolação linear da taxa CDI inicial até a taxa final informada, aplicando a taxa variável dia a dia
* **IPCA+:** fórmula de juros compostos

  ```
  (1 + IPCA) × (1 + Taxa Fixa) − 1
  ```
* **Impostos:** segue rigorosamente a tabela regressiva da Receita Federal para renda fixa baseada no prazo em dias

---

## 🤝 Contribuição

Contribuições são bem-vindas!

Sinta-se à vontade para:

* Abrir *issues*
* Enviar *pull requests*
* Sugerir melhorias na interface
* Propor novas funcionalidades
* Corrigir bugs

---

## 📄 Licença

Este projeto está sob a licença **MIT**.
Veja o arquivo `LICENSE` para mais detalhes.

---

Desenvolvido com 🐍 e ☕
