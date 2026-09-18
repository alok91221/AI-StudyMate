import io
import re

import streamlit as st

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)
from reportlab.lib.units import mm

from config import (
    MAX_IMAGE_SIZE_MB,
    MAX_IMAGES_PER_SESSION
)

from prompts.study_prompt import STUDY_PROMPT

from services.gemini_service import (
    create_gemini_client,
    analyze_images,
    GeminiQuotaError,
    GeminiTemporaryError
)

from services.chat_service import send_chat_message

from utils.file_utils import validate_image


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="AI StudyMate",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# STYLING
# =========================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    .hero-box {
        padding: 2rem;
        border-radius: 24px;
        margin-bottom: 2rem;
        border: 1px solid rgba(128, 128, 128, 0.25);
    }

    .hero-title {
        font-size: 2.8rem;
        font-weight: 800;
        letter-spacing: -1px;
        margin-bottom: 0.5rem;
    }

    .hero-subtitle {
        font-size: 1.05rem;
        line-height: 1.7;
        opacity: 0.75;
    }

    .section-title {
        font-size: 1.55rem;
        font-weight: 750;
        margin-top: 1.5rem;
        margin-bottom: 0.3rem;
    }

    .section-description {
        opacity: 0.65;
        margin-bottom: 1rem;
    }

    .focus-card {
        padding: 1rem;
        border-radius: 16px;
        border: 1px solid rgba(128, 128, 128, 0.25);
        margin-bottom: 0.5rem;
    }

    .stButton > button {
        border-radius: 12px;
        font-weight: 650;
        min-height: 2.7rem;
    }

    .stDownloadButton > button {
        border-radius: 12px;
        font-weight: 650;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SESSION STATE
# =========================================================

if "study_result" not in st.session_state:
    st.session_state.study_result = None

if "study_model" not in st.session_state:
    st.session_state.study_model = None

if "study_context" not in st.session_state:
    st.session_state.study_context = {}

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}

if "quiz_checked" not in st.session_state:
    st.session_state.quiz_checked = False

if "quiz_score" not in st.session_state:
    st.session_state.quiz_score = None


# =========================================================
# GEMINI CLIENT
# =========================================================

try:

    api_key = st.secrets["GEMINI_API_KEY"]

except Exception:

    st.error(
        "Gemini API key was not found. "
        "Please check .streamlit/secrets.toml."
    )

    st.stop()


client = create_gemini_client(api_key)


# =========================================================
# PDF GENERATION
# =========================================================

def create_pdf(text):
    """
    Convert generated study material into a PDF.
    """

    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm
    )

    styles = getSampleStyleSheet()

    title_style = styles["Title"]
    title_style.alignment = TA_CENTER

    heading_style = styles["Heading2"]

    body_style = styles["BodyText"]

    story = []

    story.append(
        Paragraph(
            "AI StudyMate - Study Notes",
            title_style
        )
    )

    story.append(
        Spacer(1, 10)
    )

    for line in text.splitlines():

        line = line.strip()

        if not line:

            story.append(
                Spacer(1, 6)
            )

            continue

        if line.startswith("## "):

            heading = line.replace(
                "## ",
                "",
                1
            ).strip()

            story.append(
                Paragraph(
                    heading,
                    heading_style
                )
            )

            story.append(
                Spacer(1, 4)
            )

        else:

            safe_line = (
                line
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )

            safe_line = safe_line.replace(
                "**",
                ""
            )

            story.append(
                Paragraph(
                    safe_line,
                    body_style
                )
            )

            story.append(
                Spacer(1, 3)
            )

    document.build(story)

    buffer.seek(0)

    return buffer.getvalue()


# =========================================================
# MCQ PARSER
# =========================================================

def parse_mcqs(text):
    """
    Extract MCQs from the generated study material.
    """

    if "MCQS" not in text.upper():

        return []

    section_match = re.search(
        r"##\s*MCQS(.*?)(?=\n##\s|\Z)",
        text,
        re.IGNORECASE | re.DOTALL
    )

    if not section_match:

        return []

    mcq_text = section_match.group(1)

    pattern = re.compile(
        r"MCQ\s*(\d+)\s*:"
        r".*?"
        r"Question:\s*(.*?)\s*"
        r"A\.\s*(.*?)\s*"
        r"B\.\s*(.*?)\s*"
        r"C\.\s*(.*?)\s*"
        r"D\.\s*(.*?)\s*"
        r"Correct Answer:\s*([ABCD])\s*"
        r"Explanation:\s*(.*?)(?=\n\s*MCQ\s*\d+\s*:|\Z)",
        re.IGNORECASE | re.DOTALL
    )

    matches = pattern.findall(mcq_text)

    mcqs = []

    for match in matches:

        (
            number,
            question,
            option_a,
            option_b,
            option_c,
            option_d,
            correct,
            explanation
        ) = match

        mcqs.append(
            {
                "number": number,
                "question": question.strip(),
                "options": {
                    "A": option_a.strip(),
                    "B": option_b.strip(),
                    "C": option_c.strip(),
                    "D": option_d.strip()
                },
                "correct": correct.upper(),
                "explanation": explanation.strip()
            }
        )

    return mcqs


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.title("📚 AI StudyMate")

    st.caption(
        "Multimodal AI study assistant"
    )

    st.divider()

    st.subheader("🎯 What you can study")

    st.markdown(
        """
        📄 Textbook pages

        📐 Diagrams

        📊 Charts & graphs

        📋 Tables

        🗺️ Maps

        🧮 Formulas

        ✍️ Handwritten notes
        """
    )

    st.divider()

    st.subheader("⚡ Workflow")

    st.markdown(
        """
        **1. Upload**

        **2. Set preferences**

        **3. Analyze**

        **4. Learn**

        **5. Take quiz**

        **6. Ask questions**
        """
    )

    st.divider()

    st.caption(
        f"Maximum image size: "
        f"{MAX_IMAGE_SIZE_MB} MB"
    )

    st.caption(
        f"Maximum images: "
        f"{MAX_IMAGES_PER_SESSION}"
    )


# =========================================================
# HERO
# =========================================================

st.markdown(
    """
    <div class="hero-box">
    """,
    unsafe_allow_html=True
)

st.caption("✨ MULTIMODAL AI LEARNING")

st.markdown(
    '<div class="hero-title">AI StudyMate</div>',
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="hero-subtitle">
    Turn textbook pages, diagrams, charts, graphs, formulas,
    and notes into personalized study material, exam questions,
    MCQs, revision points, quizzes, and interactive explanations.
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    "</div>",
    unsafe_allow_html=True
)


# =========================================================
# STUDY PREFERENCES
# =========================================================

st.markdown(
    '<div class="section-title">⚙️ Study Preferences</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-description">'
    'Tell AI StudyMate how you want the material explained.'
    '</div>',
    unsafe_allow_html=True
)


context_col1, context_col2 = st.columns(2)

with context_col1:

    class_grade = st.selectbox(
        "Class / Grade",
        [
            "Class 6",
            "Class 7",
            "Class 8",
            "Class 9",
            "Class 10",
            "Class 11",
            "Class 12",
            "College / University",
            "Other"
        ]
    )


with context_col2:

    subject = st.text_input(
        "Subject",
        placeholder="Example: Physics, Biology, History"
    )


exam_type = st.selectbox(
    "Exam Type",
    [
        "School Exam",
        "Board Exam",
        "Competitive Exam",
        "College Exam",
        "General Revision",
        "Other"
    ]
)


pref_col1, pref_col2 = st.columns(2)

with pref_col1:

    difficulty = st.selectbox(
        "Difficulty Level",
        [
            "Beginner",
            "Intermediate",
            "Advanced"
        ]
    )


with pref_col2:

    language = st.selectbox(
        "Language",
        [
            "English",
            "Hindi"
        ]
    )


# =========================================================
# FOCUS MODE
# =========================================================

st.markdown(
    '<div class="section-title">🎯 Focus Mode</div>',
    unsafe_allow_html=True
)

focus_mode = st.radio(
    "Choose how AI StudyMate should focus on your material:",
    [
        "⚡ Quick Revision",
        "📚 Detailed Learning",
        "🎯 Exam Preparation",
        "🧒 Explain Like I'm 10"
    ],
    horizontal=True
)


focus_mode_map = {
    "⚡ Quick Revision": "Quick Revision",
    "📚 Detailed Learning": "Detailed Learning",
    "🎯 Exam Preparation": "Exam Preparation",
    "🧒 Explain Like I'm 10": "Explain Like I'm 10"
}


selected_focus_mode = focus_mode_map[focus_mode]


custom_instruction = st.text_area(
    "Optional instructions",
    placeholder=(
        "Example: Focus on important formulas, "
        "explain the diagram step by step, "
        "or give extra examples."
    )
)


# =========================================================
# UPLOAD
# =========================================================

st.markdown(
    '<div class="section-title">📷 Study Material</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-description">'
    f'Upload up to {MAX_IMAGES_PER_SESSION} images '
    'from your textbook or study notes.'
    '</div>',
    unsafe_allow_html=True
)


uploaded_files = st.file_uploader(
    "Choose study images",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)


if uploaded_files:

    if len(uploaded_files) > MAX_IMAGES_PER_SESSION:

        st.error(
            f"You can upload a maximum of "
            f"{MAX_IMAGES_PER_SESSION} images."
        )

    else:

        st.success(
            f"{len(uploaded_files)} image(s) ready."
        )

        for uploaded_file in uploaded_files:

            st.write(
                f"📄 **{uploaded_file.name}**"
            )


# =========================================================
# ANALYZE
# =========================================================

analyze_button = st.button(
    "🔍 Analyze Study Material",
    type="primary",
    width="stretch"
)


if analyze_button:

    if not uploaded_files:

        st.warning(
            "Please upload at least one study image."
        )

    elif len(uploaded_files) > MAX_IMAGES_PER_SESSION:

        st.error(
            f"Please upload no more than "
            f"{MAX_IMAGES_PER_SESSION} images."
        )

    elif not subject.strip():

        st.warning(
            "Please enter the subject."
        )

    else:

        images = []

        validation_failed = False

        for uploaded_file in uploaded_files:

            is_valid, error_message = validate_image(
                uploaded_file
            )

            if not is_valid:

                st.error(
                    f"{uploaded_file.name}: "
                    f"{error_message}"
                )

                validation_failed = True

                break

            images.append(
                {
                    "image_bytes": uploaded_file.getvalue(),
                    "mime_type": uploaded_file.type
                }
            )

        if not validation_failed:

            final_prompt = f"""
{STUDY_PROMPT}

=========================================================
STUDENT PROFILE
=========================================================

Class / Grade:
{class_grade}

Subject:
{subject}

Exam Type:
{exam_type}

Difficulty:
{difficulty}

Language:
{language}

Focus Mode:
{selected_focus_mode}

Custom Instructions:
{
    custom_instruction
    if custom_instruction.strip()
    else "None"
}

=========================================================
FINAL INSTRUCTION
=========================================================

Create the complete study material according to
the student's profile and selected Focus Mode.

Write the complete answer in {language}.
"""

            with st.spinner(
                "📚 AI StudyMate is analyzing your material..."
            ):

                try:

                    result, model_used = analyze_images(
                        client,
                        images,
                        final_prompt
                    )

                    st.session_state.study_result = result

                    st.session_state.study_model = model_used

                    st.session_state.study_context = {
                        "class_grade": class_grade,
                        "subject": subject,
                        "exam_type": exam_type,
                        "difficulty": difficulty,
                        "language": language,
                        "focus_mode": selected_focus_mode
                    }

                    st.session_state.chat_messages = []

                    st.session_state.quiz_answers = {}

                    st.session_state.quiz_checked = False

                    st.session_state.quiz_score = None

                    st.success(
                        "Study material analyzed successfully!"
                    )

                except GeminiQuotaError as error:

                    st.error(
                        "⚠️ All configured Gemini models "
                        "have reached their current quota."
                    )

                    st.info(
                        "The automatic fallback chain was checked."
                    )

                    with st.expander(
                        "Technical details"
                    ):

                        st.code(str(error))

                except GeminiTemporaryError:

                    st.error(
                        "⚠️ Gemini is temporarily unavailable. "
                        "Please try again later."
                    )

                except Exception as error:

                    st.error(
                        "❌ Something went wrong while analyzing "
                        "the study material."
                    )

                    with st.expander(
                        "Technical details"
                    ):

                        st.code(str(error))


# =========================================================
# DISPLAY RESULT
# =========================================================

if st.session_state.study_result:

    result = st.session_state.study_result

    st.divider()

    st.markdown(
        '<div class="section-title">'
        '📖 Your Study Material'
        '</div>',
        unsafe_allow_html=True
    )

    if st.session_state.study_model:

        st.caption(
            f"🤖 Generated using Gemini: "
            f"`{st.session_state.study_model}`"
        )

    context = st.session_state.study_context

    if context:

        st.caption(
            f"📚 {context.get('class_grade', '')} • "
            f"{context.get('subject', '')} • "
            f"{context.get('exam_type', '')} • "
            f"{context.get('focus_mode', '')}"
        )


    # =====================================================
    # PARSE SECTIONS
    # =====================================================

    sections = {}

    current_section = "GENERAL"

    sections[current_section] = []

    for line in result.splitlines():

        stripped_line = line.strip()

        if stripped_line.startswith("## "):

            current_section = (
                stripped_line
                .replace("## ", "", 1)
                .strip()
                .upper()
            )

            sections[current_section] = []

        else:

            sections[current_section].append(line)


    for section_name in sections:

        sections[section_name] = "\n".join(
            sections[section_name]
        ).strip()


    # =====================================================
    # MAIN STUDY TABS
    # =====================================================

    tab_names = [
        "TOPIC",
        "IMPORTANT INFORMATION",
        "SIMPLE EXPLANATION",
        "IMPORTANT TERMS",
        "KEY CONCEPTS",
        "SUMMARY",
        "IMPORTANT QUESTIONS",
        "MCQS",
        "EXAM REVISION POINTS"
    ]


    available_tabs = [
        name
        for name in tab_names
        if name in sections
    ]


    if available_tabs:

        tabs = st.tabs(available_tabs)

        for tab, section_name in zip(
            tabs,
            available_tabs
        ):

            with tab:

                content = sections[section_name]

                if content:

                    st.markdown(content)

                else:

                    st.info(
                        "No information was generated "
                        "for this section."
                    )


    # =====================================================
    # VISUAL ANALYSIS
    # =====================================================

    st.markdown(
        '<div class="section-title">'
        '🔎 Visual Analysis'
        '</div>',
        unsafe_allow_html=True
    )


    if "DIAGRAM ANALYSIS" in sections:

        with st.expander(
            "📐 Diagram Analysis"
        ):

            st.markdown(
                sections["DIAGRAM ANALYSIS"]
            )


    if "CHART OR GRAPH ANALYSIS" in sections:

        with st.expander(
            "📊 Chart / Graph Analysis"
        ):

            st.markdown(
                sections["CHART OR GRAPH ANALYSIS"]
            )


    if "FORMULA ANALYSIS" in sections:

        with st.expander(
            "🧮 Formula Analysis"
        ):

            st.markdown(
                sections["FORMULA ANALYSIS"]
            )


    # =====================================================
    # STUDY TIP
    # =====================================================

    if "STUDY TIP" in sections:

        st.markdown(
            '<div class="section-title">'
            '💡 Study Tip'
            '</div>',
            unsafe_allow_html=True
        )

        st.info(
            sections["STUDY TIP"]
        )


    # =====================================================
    # INTERACTIVE QUIZ
    # =====================================================

    st.divider()

    st.markdown(
        '<div class="section-title">'
        '🧠 Interactive Quiz'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-description">'
        'Test yourself using the 5 MCQs generated from '
        'your study material.'
        '</div>',
        unsafe_allow_html=True
    )


    mcqs = parse_mcqs(result)


    if len(mcqs) >= 5:

        for index, mcq in enumerate(mcqs[:5]):

            st.markdown(
                f"### Question {index + 1}"
            )

            st.write(
                mcq["question"]
            )

            option_labels = [
                "A",
                "B",
                "C",
                "D"
            ]

            options = [
                f"{letter}. "
                f"{mcq['options'][letter]}"
                for letter in option_labels
            ]

            selected_option = st.radio(
                "Choose your answer:",
                options,
                key=f"quiz_question_{index}",
                index=None
            )

            if selected_option:

                selected_letter = selected_option[0]

                st.session_state.quiz_answers[index] = (
                    selected_letter
                )


        check_quiz = st.button(
            "✅ Check Answers",
            key="check_quiz"
        )


        if check_quiz:

            score = 0

            for index, mcq in enumerate(mcqs[:5]):

                selected = st.session_state.quiz_answers.get(
                    index
                )

                if selected == mcq["correct"]:

                    score += 1

            st.session_state.quiz_score = score

            st.session_state.quiz_checked = True


        if st.session_state.quiz_checked:

            score = st.session_state.quiz_score

            st.success(
                f"🎉 Your score: {score}/5"
            )

            for index, mcq in enumerate(mcqs[:5]):

                selected = st.session_state.quiz_answers.get(
                    index
                )

                correct = mcq["correct"]

                if selected == correct:

                    st.markdown(
                        f"**Question {index + 1}: ✅ Correct**"
                    )

                else:

                    st.markdown(
                        f"**Question {index + 1}: ❌ Incorrect**"
                    )

                    st.write(
                        f"Correct answer: **{correct}**"
                    )

                st.caption(
                    mcq["explanation"]
                )

    else:

        st.info(
            "The generated MCQs could not be parsed "
            "into the interactive quiz format."
        )


    # =====================================================
    # REGENERATE
    # =====================================================

    st.divider()

    st.markdown(
        '<div class="section-title">'
        '🔄 Regenerate'
        '</div>',
        unsafe_allow_html=True
    )

    regenerate_button = st.button(
        "🔄 Regenerate Study Material",
        width="stretch"
    )


    if regenerate_button:

        context = st.session_state.study_context

        if uploaded_files:

            images = []

            for uploaded_file in uploaded_files:

                is_valid, error_message = validate_image(
                    uploaded_file
                )

                if is_valid:

                    images.append(
                        {
                            "image_bytes": uploaded_file.getvalue(),
                            "mime_type": uploaded_file.type
                        }
                    )

            if images:

                regenerate_prompt = f"""
{STUDY_PROMPT}

STUDENT PROFILE:

Class / Grade:
{context.get('class_grade', 'Not specified')}

Subject:
{context.get('subject', 'Not specified')}

Exam Type:
{context.get('exam_type', 'General Revision')}

Difficulty:
{context.get('difficulty', 'Beginner')}

Language:
{context.get('language', 'English')}

Focus Mode:
{context.get('focus_mode', 'Detailed Learning')}

Regenerate the study material with fresh wording
while preserving factual accuracy and grounding
the content in the uploaded material.
"""

                with st.spinner(
                    "🔄 Regenerating study material..."
                ):

                    try:

                        new_result, new_model = analyze_images(
                            client,
                            images,
                            regenerate_prompt
                        )

                        st.session_state.study_result = new_result

                        st.session_state.study_model = new_model

                        st.session_state.chat_messages = []

                        st.session_state.quiz_answers = {}

                        st.session_state.quiz_checked = False

                        st.session_state.quiz_score = None

                        st.rerun()

                    except GeminiQuotaError:

                        st.error(
                            "⚠️ All configured Gemini models "
                            "have reached their current quota."
                        )

                    except GeminiTemporaryError:

                        st.error(
                            "⚠️ Gemini is temporarily unavailable."
                        )

                    except Exception as error:

                        st.error(
                            "❌ Regeneration failed."
                        )

                        st.code(str(error))

            else:

                st.warning(
                    "Please keep the uploaded images available "
                    "to regenerate the material."
                )

        else:

            st.warning(
                "Please upload the original study images again "
                "before regenerating."
            )


    # =====================================================
    # PDF EXPORT
    # =====================================================

    st.divider()

    st.markdown(
        '<div class="section-title">'
        '📥 Export'
        '</div>',
        unsafe_allow_html=True
    )


    pdf_bytes = create_pdf(result)


    st.download_button(
        label="📄 Download Study Notes as PDF",
        data=pdf_bytes,
        file_name="AI_StudyMate_Study_Notes.pdf",
        mime="application/pdf",
        width="stretch"
    )


    # =====================================================
    # STUDY CHAT
    # =====================================================

    st.divider()

    st.markdown(
        '<div class="section-title">'
        '💬 Study Chat'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-description">'
        'Ask questions about your uploaded study material.'
        '</div>',
        unsafe_allow_html=True
    )


    # -----------------------------------------------------
    # CHAT HISTORY
    # -----------------------------------------------------

    for message in st.session_state.chat_messages:

        if message["role"] == "user":

            with st.chat_message("user"):

                st.write(
                    message["content"]
                )

        else:

            with st.chat_message("assistant"):

                st.markdown(
                    message["content"]
                )

                if message.get("model"):

                    st.caption(
                        f"🤖 Gemini: "
                        f"`{message['model']}`"
                    )


    # -----------------------------------------------------
    # CHAT INPUT
    # -----------------------------------------------------

    user_message = st.chat_input(
        "Ask a question about your study material..."
    )


    if user_message:

        question = user_message.strip()

        st.session_state.chat_messages.append(
            {
                "role": "user",
                "content": question
            }
        )


        with st.spinner(
            "🤔 AI StudyMate is thinking..."
        ):

            try:

                answer, model_used = send_chat_message(
                    client,
                    st.session_state.study_result,
                    st.session_state.chat_messages[:-1],
                    question
                )

                st.session_state.chat_messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "model": model_used
                    }
                )

                st.rerun()

            except GeminiQuotaError:

                st.error(
                    "⚠️ All configured Gemini models "
                    "have reached their current quota."
                )

                st.session_state.chat_messages.pop()

            except GeminiTemporaryError:

                st.error(
                    "⚠️ Gemini is temporarily unavailable."
                )

                st.session_state.chat_messages.pop()

            except Exception as error:

                st.error(
                    "❌ I couldn't answer that right now."
                )

                with st.expander(
                    "Technical details"
                ):

                    st.code(str(error))

                st.session_state.chat_messages.pop()


# =========================================================
# START NEW SESSION
# =========================================================

st.divider()

if st.button(
    "🔄 Start New Study Session",
    width="stretch"
):

    st.session_state.study_result = None

    st.session_state.study_model = None

    st.session_state.study_context = {}

    st.session_state.chat_messages = []

    st.session_state.quiz_answers = {}

    st.session_state.quiz_checked = False

    st.session_state.quiz_score = None

    st.rerun()