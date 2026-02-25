# 📋 Questionnaire Designer

Ferramenta de IA para criar questionários profissionais de pesquisa de mercado a partir do briefing do projeto.

**Grátis. Sem instalação. Só abrir o link.**

---

## Como usar (2 minutos)

### Passo 1: Obter API Key gratuita do Google

1. Acesse [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Faça login com sua conta Google
3. Clique em **"Create API Key"**
4. Copie a chave gerada

> A API Key é **gratuita** e permite ~1500 requisições por dia — mais do que suficiente.

### Passo 2: Acessar o app

**Opção A — Link online (recomendado):**

Acesse o link compartilhado pelo administrador do projeto. O app roda no navegador, sem instalar nada.

**Opção B — Rodar localmente:**

```bash
# Clonar o repositório
git clone <url-do-repositorio>
cd questionnaire-designer

# Instalar dependências
pip install -r requirements.txt

# Rodar o app
streamlit run app.py
```

O app abrirá em `http://localhost:8501`

### Passo 3: Usar

1. Cole sua API Key na barra lateral
2. Faça upload dos documentos do projeto (briefing, proposta, docs do cliente)
3. Configure tipo de pesquisa, público-alvo e LOI
4. Clique em **"Gerar Questionário"**
5. Revise, refine via chat se necessário
6. Exporte o .docx final

---

## Deploy no Streamlit Cloud (para o admin)

Para disponibilizar o app online para toda a equipe:

1. Crie um repositório no GitHub com os arquivos do projeto
2. Acesse [https://share.streamlit.io](https://share.streamlit.io)
3. Conecte sua conta GitHub
4. Selecione o repositório e o arquivo `app.py`
5. Clique em **Deploy**
6. Compartilhe o link gerado com a equipe

O Streamlit Cloud é **gratuito** para apps públicos.

---

## Funcionalidades

| Recurso | Descrição |
|---------|-----------|
| 📂 Upload de documentos | PDF, DOCX, PPTX, XLSX, TXT |
| 🧠 Geração inteligente | Cria questionário completo com screening, routing, escalas |
| 💬 Refinamento por chat | Peça alterações em linguagem natural |
| 📄 Export .docx | Documento formatado pronto para o cliente |
| 🔧 Export JSON | Estrutura de dados para integração |
| ✅ Boas práticas | Controle de vieses, mobile-first, MECE |

## Tipos de pesquisa suportados

- NPS / Satisfação
- Brand Awareness & Image
- Uso e Atitudes (U&A)
- Concept Test / Product Test
- Customer Experience (CX)
- Clima Organizacional
- Ad Test / Comunicação
- Pricing / Willingness to Pay

---

## Dicas para melhores resultados

1. **Quanto mais contexto, melhor**: inclua briefing, proposta, pesquisas anteriores
2. **Seja específico nas instruções adicionais**: "incluir pergunta sobre NPS do app" é melhor que "perguntar sobre app"
3. **Use o chat para refinar**: o questionário nunca fica perfeito na primeira versão
4. **Revise a lógica de routing**: o modelo é bom mas pode errar em routing complexo
5. **Sempre valide o .docx**: abra no Word e confira antes de enviar ao cliente

---

## Estrutura do projeto

```
questionnaire-designer/
├── app.py                 # App principal (Streamlit)
├── prompts.py             # System prompts do agente
├── document_parser.py     # Extração de texto de documentos
├── docx_generator.py      # Geração do arquivo Word
├── requirements.txt       # Dependências Python
└── README.md              # Este arquivo
```

---

## Limitações

- O modelo pode gerar JSON malformado ocasionalmente — basta clicar em "Gerar" novamente
- Routing muito complexo (muitos skip patterns aninhados) pode ter erros
- O .docx é um rascunho profissional, mas pode precisar de ajustes de formatação finos
- A qualidade depende da qualidade do briefing fornecido
- Limite de ~30 páginas de documentos por geração (limite de contexto do modelo)

---

## Tecnologias

- **Frontend**: Streamlit
- **LLM**: Google Gemini 2.0 Flash (API gratuita)
- **Doc generation**: python-docx
- **Hosting**: Streamlit Community Cloud (gratuito)
