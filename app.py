import streamlit as st
import json
import re
from datetime import datetime

import google.generativeai as genai

from prompts import SYSTEM_PROMPT, GENERATION_PROMPT, REFINEMENT_PROMPT
from document_parser import parse_all_files
from docx_generator import generate_questionnaire_docx

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="Questionnaire Designer",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# STYLES
# ============================================================
st.markdown(
    """
    <style>
    .stApp { max-width: 1200px; margin: 0 auto; }
    .main-title { font-size: 1.8rem; font-weight: 700; color: #1A568E; margin-bottom: 0; }
    .subtitle { font-size: 1rem; color: #777; margin-top: 0; }
    .section-card {
        background: #f8fbff; border-left: 4px solid #2E86C1;
        padding: 12px 16px; margin: 8px 0; border-radius: 0 8px 8px 0;
    }
    .question-badge {
        display: inline-block; background: #EBF5FB; color: #1A568E;
        padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600;
    }
    .stat-box {
        background: #f0f7ff; border-radius: 8px; padding: 16px;
        text-align: center; border: 1px solid #d6eaf8;
    }
    .stat-number { font-size: 1.8rem; font-weight: 700; color: #1A568E; }
    .stat-label { font-size: 0.8rem; color: #777; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# SESSION STATE
# ============================================================
if "questionnaire_json" not in st.session_state:
    st.session_state.questionnaire_json = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "project_context" not in st.session_state:
    st.session_state.project_context = ""
if "generation_step" not in st.session_state:
    st.session_state.generation_step = "setup"  # setup | generated | refining


# ============================================================
# GEMINI CLIENT
# ============================================================
def get_gemini_model(api_key: str):
    """Initialize and return the Gemini model."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=SYSTEM_PROMPT,
        generation_config=genai.GenerationConfig(
            temperature=0.4,
            max_output_tokens=8192,
        ),
    )
    return model


def extract_json_from_response(text: str) -> dict:
    """Extract JSON from model response, handling markdown code blocks."""
    # Try to find JSON in code blocks first
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))

    # Try to parse the whole text as JSON
    # Find the first { and last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return json.loads(text[start : end + 1])

    raise ValueError("Não foi possível extrair JSON da resposta do modelo.")


def generate_questionnaire(model, context: str, settings: dict) -> dict:
    """Generate a questionnaire using Gemini."""
    prompt = GENERATION_PROMPT.format(
        project_context=context,
        research_type=settings.get("research_type", "Pesquisa quantitativa"),
        target_audience=settings.get("target_audience", "Não especificado"),
        max_loi=settings.get("max_loi", 15),
        platform=settings.get("platform", "QuestionPro"),
        additional_instructions=settings.get("additional_instructions", "Nenhuma"),
    )

    response = model.generate_content(prompt)
    return extract_json_from_response(response.text)


def refine_questionnaire(model, current_json: dict, feedback: str) -> dict:
    """Refine an existing questionnaire based on feedback."""
    prompt = REFINEMENT_PROMPT.format(
        current_questionnaire=json.dumps(current_json, ensure_ascii=False, indent=2),
        feedback=feedback,
    )

    response = model.generate_content(prompt)
    return extract_json_from_response(response.text)


# ============================================================
# UI COMPONENTS
# ============================================================
def render_questionnaire_preview(q_json: dict):
    """Render a preview of the questionnaire in Streamlit."""
    project = q_json.get("project_summary", {})

    # Stats row
    total_q = project.get("total_questions", "—")
    loi = project.get("estimated_loi_minutes", "—")
    num_sections = len(q_json.get("sections", []))

    cols = st.columns(3)
    with cols[0]:
        st.markdown(
            f'<div class="stat-box"><div class="stat-number">{total_q}</div>'
            f'<div class="stat-label">Perguntas</div></div>',
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            f'<div class="stat-box"><div class="stat-number">{loi} min</div>'
            f'<div class="stat-label">LOI Estimada</div></div>',
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.markdown(
            f'<div class="stat-box"><div class="stat-number">{num_sections}</div>'
            f'<div class="stat-label">Seções</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Sections
    for section in q_json.get("sections", []):
        with st.expander(
            f"📁 {section['id']}. {section['title']} ({len(section.get('questions', []))} perguntas)",
            expanded=False,
        ):
            if section.get("description"):
                st.caption(section["description"])

            for q in section.get("questions", []):
                q_type = q.get("type", "")
                type_emoji = {
                    "single_choice": "⏺",
                    "multiple_choice": "☑️",
                    "scale_numeric": "🔢",
                    "scale_likert": "📊",
                    "nps": "📈",
                    "ranking": "🏆",
                    "open_text": "✏️",
                    "matrix": "📋",
                }.get(q_type, "❓")

                st.markdown(
                    f'<span class="question-badge">{q["id"]}</span> {type_emoji} **{q["text"]}**',
                    unsafe_allow_html=True,
                )

                # Show options for choice questions
                if q_type in ("single_choice", "multiple_choice"):
                    options = q.get("options", [])
                    for opt in options:
                        if isinstance(opt, dict):
                            routing = opt.get("routing", "")
                            routing_tag = ""
                            if routing == "TERMINATE":
                                routing_tag = " 🔴 ENCERRAR"
                            elif routing and routing != "CONTINUE":
                                routing_tag = f" 🟡 → {routing}"
                            st.markdown(
                                f"&nbsp;&nbsp;&nbsp;&nbsp;`{opt.get('code', '')}` {opt.get('text', '')}{routing_tag}"
                            )
                        else:
                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;• {opt}")

                elif q_type in ("scale_numeric", "nps"):
                    anchor_min = q.get("anchor_min", "")
                    anchor_max = q.get("anchor_max", "")
                    scale_min = q.get("scale_min", 0)
                    scale_max = q.get("scale_max", 10)
                    st.markdown(
                        f"&nbsp;&nbsp;&nbsp;&nbsp;`{scale_min}` {anchor_min} ← → {anchor_max} `{scale_max}`"
                    )

                # Notes
                if q.get("programming_note"):
                    st.markdown(
                        f"&nbsp;&nbsp;&nbsp;&nbsp;📋 _{q['programming_note']}_"
                    )
                if q.get("methodological_note"):
                    st.markdown(
                        f"&nbsp;&nbsp;&nbsp;&nbsp;🔬 _{q['methodological_note']}_"
                    )

                st.markdown("")  # spacer

    # Methodology notes
    notes = q_json.get("methodological_notes", {})
    if notes:
        with st.expander("📑 Notas Metodológicas", expanded=False):
            if notes.get("sampling"):
                st.markdown(f"**Amostragem:** {notes['sampling']}")
            if notes.get("quotas"):
                st.markdown(f"**Cotas:** {notes['quotas']}")
            if notes.get("limitations"):
                st.markdown(f"**Limitações:** {notes['limitations']}")
            biases = notes.get("biases_mitigated", [])
            if biases:
                st.markdown("**Vieses controlados:**")
                for b in biases:
                    st.markdown(f"- {b}")


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("### ⚙️ Configuração")

    api_key = st.text_input(
        "API Key do Google Gemini",
        type="password",
        help="Grátis em https://aistudio.google.com/apikey",
    )

    st.markdown("---")

    st.markdown("### 📂 Documentos do Projeto")
    uploaded_files = st.file_uploader(
        "Upload briefing, proposta, docs do cliente",
        accept_multiple_files=True,
        type=["pdf", "docx", "txt", "pptx", "xlsx", "md"],
        help="Formatos aceitos: PDF, DOCX, TXT, PPTX, XLSX",
    )

    if uploaded_files:
        st.success(f"{len(uploaded_files)} arquivo(s) carregado(s)")
        for f in uploaded_files:
            st.caption(f"📄 {f.name}")

    st.markdown("---")

    st.markdown("### 🎯 Configurações da Pesquisa")

    research_type = st.selectbox(
        "Tipo de pesquisa",
        [
            "NPS / Satisfação",
            "Brand Awareness & Image",
            "Uso e Atitudes (U&A)",
            "Concept Test / Product Test",
            "Customer Experience (CX)",
            "Clima Organizacional",
            "Ad Test / Comunicação",
            "Pricing / Willingness to Pay",
            "Outro",
        ],
    )

    target_audience = st.text_input(
        "Público-alvo",
        placeholder="Ex: Lojistas que usam maquininha há 6+ meses",
    )

    max_loi = st.slider("LOI máxima (minutos)", 5, 30, 12)

    platform = st.selectbox(
        "Plataforma de campo",
        ["QuestionPro", "SurveyMonkey", "Typeform", "Google Forms", "Qualtrics", "Outra"],
    )

    additional_instructions = st.text_area(
        "Instruções adicionais",
        placeholder="Ex: Incluir perguntas sobre o app mobile. Comparar com wave 2023.",
        height=100,
    )

    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #999; font-size: 0.75rem;">
            Questionnaire Designer v1.0<br>
            Powered by Gemini 2.0 Flash<br>
            <a href="https://aistudio.google.com/apikey" target="_blank">
                Obter API Key gratuita
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# MAIN CONTENT
# ============================================================
st.markdown('<p class="main-title">📋 Questionnaire Designer</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">Crie questionários profissionais de pesquisa de mercado a partir do briefing do projeto</p>',
    unsafe_allow_html=True,
)
st.markdown("---")


# --- STEP 1: Generate ---
if st.session_state.generation_step == "setup":

    # Show extracted context if files uploaded
    if uploaded_files:
        with st.expander("👁️ Conteúdo extraído dos documentos", expanded=False):
            context = parse_all_files(uploaded_files)
            st.session_state.project_context = context
            st.text(context[:3000] + ("..." if len(context) > 3000 else ""))
            st.caption(f"Total: {len(context)} caracteres extraídos")

    # Context box for additional manual input
    manual_context = st.text_area(
        "📝 Contexto adicional (opcional)",
        placeholder="Cole aqui informações extras sobre o projeto, objetivos específicos, hipóteses...",
        height=150,
    )

    if manual_context:
        st.session_state.project_context = (
            st.session_state.project_context + "\n\n--- Contexto adicional ---\n" + manual_context
        )

    # Generate button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        generate_btn = st.button(
            "🚀 Gerar Questionário",
            use_container_width=True,
            type="primary",
            disabled=not api_key,
        )

    if not api_key:
        st.info("👈 Insira sua API Key do Google Gemini na barra lateral para começar.")

    if generate_btn and api_key:
        if not st.session_state.project_context.strip() and not manual_context:
            st.warning("Faça upload de documentos ou insira contexto manualmente.")
        else:
            with st.spinner("🧠 Analisando documentos e desenhando questionário..."):
                try:
                    model = get_gemini_model(api_key)
                    settings = {
                        "research_type": research_type,
                        "target_audience": target_audience,
                        "max_loi": max_loi,
                        "platform": platform,
                        "additional_instructions": additional_instructions,
                    }
                    result = generate_questionnaire(
                        model, st.session_state.project_context, settings
                    )
                    st.session_state.questionnaire_json = result
                    st.session_state.generation_step = "generated"
                    st.rerun()
                except json.JSONDecodeError as e:
                    st.error(f"Erro ao interpretar resposta do modelo. Tente novamente.\n\nDetalhe: {e}")
                except Exception as e:
                    error_msg = str(e)
                    if "API_KEY" in error_msg.upper() or "401" in error_msg or "403" in error_msg:
                        st.error("API Key inválida. Verifique sua chave em https://aistudio.google.com/apikey")
                    else:
                        st.error(f"Erro: {e}")


# --- STEP 2: Review & Refine ---
elif st.session_state.generation_step in ("generated", "refining"):

    q_json = st.session_state.questionnaire_json

    if q_json:
        # Tabs
        tab_preview, tab_refine, tab_json, tab_export = st.tabs(
            ["👁️ Preview", "💬 Refinar", "🔧 JSON", "📥 Exportar"]
        )

        with tab_preview:
            render_questionnaire_preview(q_json)

        with tab_refine:
            st.markdown("### Refine o questionário via chat")
            st.markdown(
                "Peça alterações em linguagem natural. Exemplos:\n"
                '- *"Adicione uma pergunta sobre frequência de uso do app"*\n'
                '- *"Remova a seção de dados demográficos"*\n'
                '- *"Troque a escala da Q5 para Likert de 5 pontos"*\n'
                '- *"Adicione uma pergunta de MaxDiff com os atributos: preço, qualidade, atendimento, velocidade"*'
            )

            # Chat history
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            # Chat input
            feedback = st.chat_input("Descreva as alterações desejadas...")

            if feedback and api_key:
                st.session_state.chat_history.append(
                    {"role": "user", "content": feedback}
                )

                with st.spinner("🔄 Aplicando alterações..."):
                    try:
                        model = get_gemini_model(api_key)
                        updated = refine_questionnaire(model, q_json, feedback)
                        st.session_state.questionnaire_json = updated
                        st.session_state.generation_step = "refining"
                        st.session_state.chat_history.append(
                            {
                                "role": "assistant",
                                "content": "✅ Questionário atualizado! Veja a aba **Preview** para conferir as mudanças.",
                            }
                        )
                        st.rerun()
                    except Exception as e:
                        st.session_state.chat_history.append(
                            {
                                "role": "assistant",
                                "content": f"❌ Erro ao aplicar alterações: {e}. Tente reformular o pedido.",
                            }
                        )
                        st.rerun()

        with tab_json:
            st.markdown("### JSON do Questionário")
            st.caption("Você pode editar diretamente e clicar em 'Aplicar JSON'.")

            json_str = json.dumps(q_json, ensure_ascii=False, indent=2)
            edited_json = st.text_area(
                "JSON",
                value=json_str,
                height=500,
                label_visibility="collapsed",
            )

            if st.button("Aplicar JSON editado"):
                try:
                    parsed = json.loads(edited_json)
                    st.session_state.questionnaire_json = parsed
                    st.success("JSON atualizado!")
                    st.rerun()
                except json.JSONDecodeError as e:
                    st.error(f"JSON inválido: {e}")

        with tab_export:
            st.markdown("### Exportar Questionário")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 📄 Word (.docx)")
                st.markdown("Documento formatado pronto para enviar ao cliente ou à equipe.")

                try:
                    docx_bytes = generate_questionnaire_docx(q_json)
                    project_name = q_json.get("project_summary", {}).get(
                        "research_objective", "questionario"
                    )
                    safe_name = re.sub(r"[^\w\s-]", "", project_name)[:50].strip()
                    filename = f"questionario_{safe_name}_{datetime.now().strftime('%Y%m%d')}.docx"

                    st.download_button(
                        label="⬇️ Baixar .docx",
                        data=docx_bytes,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                        type="primary",
                    )
                except Exception as e:
                    st.error(f"Erro ao gerar DOCX: {e}")

            with col2:
                st.markdown("#### 🔧 JSON")
                st.markdown("Estrutura de dados para integração com plataformas ou outros agentes.")

                json_export = json.dumps(q_json, ensure_ascii=False, indent=2)
                st.download_button(
                    label="⬇️ Baixar .json",
                    data=json_export,
                    file_name=f"questionario_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json",
                    use_container_width=True,
                )

    # Reset button
    st.markdown("---")
    if st.button("🔄 Começar novo questionário"):
        st.session_state.questionnaire_json = None
        st.session_state.chat_history = []
        st.session_state.project_context = ""
        st.session_state.generation_step = "setup"
        st.rerun()
