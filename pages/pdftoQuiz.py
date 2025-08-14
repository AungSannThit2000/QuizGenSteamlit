# pages/03_PDF_Quiz_OpenAI.py
# ------------------------------------------------------------
# PDF ➜ Quiz (OpenAI Direct) — no preview, detailed prompts
# - Multiple PDF upload
# - New SDK (>=1.0): from openai import OpenAI
# - Detailed prompts per difficulty level (Bloom’s)
# - Generate, expanders, check answers, download, clear
#
# Setup:
#   pip install streamlit PyPDF2 python-dotenv openai
#   export OPENAI_API_KEY=sk-...
# Run:
#   streamlit run imagetoQuiz.py
# ------------------------------------------------------------

from __future__ import annotations
import os, re, json
from typing import Dict, Any, List

import streamlit as st
from PyPDF2 import PdfReader
from openai import OpenAI

# Optional .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ---------------------------
# Helpers
# ---------------------------
def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("Missing OPENAI_API_KEY environment variable.")
        st.stop()
    return OpenAI(api_key=api_key)

def extract_text_from_pdf(file) -> str:
    reader = PdfReader(file)
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(parts)

def sanitize_user_prompt(user_input: str | None) -> str:
    if not user_input:
        return ""
    bad = [
        r"(?i)\byou are an\b", r"(?i)ignore previous", r"(?i)\bact as\b",
        r"(?i)disregard", r"(?i)^system:", r"(?i)^user:", r"(?i)^assistant:"
    ]
    for pat in bad:
        user_input = re.sub(pat, "", user_input)
    return user_input.strip()

def prompt_for(difficulty: str, n: int, extra: str) -> str:
    extra = sanitize_user_prompt(extra)
    d = (difficulty or "easy").lower()

    shared_rules = (
        "Format rules:\n"
        "1) Return STRICT JSON only (no markdown, backticks, or commentary).\n"
        "2) JSON schema: {\"questions\":[{\"question\":\"...\",\"options\":[\"...\",\"...\",\"...\",\"...\"],\"answer\":\"...\"}]}.\n"
        "3) Exactly 4 options per item; plausible distractors; avoid 'All of the above/None of the above'.\n"
        "4) The answer string must exactly match one of the options.\n"
        "5) Base all content ONLY on the provided PDF text.\n"
        "6) Clear, single-focus items; avoid ambiguity and double-negatives.\n"
    )

    if d == "easy":
        level_rules = (
            f"Task: Generate {n} MCQs at **Remembering/Understanding** levels of Bloom's.\n"
            "- Focus: facts, definitions, key terms, purposes, simple interpretations.\n"
            "- Cognitive ops: recognize, recall, define, identify, classify, summarize.\n"
            "Suggested question-stem patterns:\n"
            "• Which of the following best defines <term>?\n"
            "• According to the text, what is the purpose of <X>?\n"
            "• <Concept> is primarily associated with which of the following?\n"
            "• Which statement is TRUE about <topic>?\n"
            "• Identify the correct sequence/element/label for <diagram/text excerpt>.\n"
        )
    elif d == "medium":
        level_rules = (
            f"Task: Generate {n} MCQs at **Applying/Analyzing** levels of Bloom's.\n"
            "- Focus: applying procedures, interpreting data/figures, comparing/contrasting, categorizing, inference.\n"
            "- Cognitive ops: apply, compute, infer, organize, differentiate, compare.\n"
            "Suggested question-stem patterns:\n"
            "• Given the scenario, which approach should be applied first?\n"
            "• Which inference can be drawn from the data/example provided in the text?\n"
            "• Which option best completes the classification of <items>?\n"
            "• Compared with <A>, <B> primarily differs in which aspect?\n"
            "• What is the most appropriate calculation/step to solve <problem> using the method described?\n"
        )
    else:
        level_rules = (
            f"Task: Generate {n} MCQs at **Evaluating/Creating** levels of Bloom's with a strong **case-study** focus.\n"
            "- For at least HALF of the questions, include a **2–3 sentence mini case** derived from the text (synthesize details; do not invent facts beyond it).\n"
            "- Focus: critique decisions, weigh trade-offs, choose optimal designs/strategies, predict outcomes, justify selections.\n"
            "- Cognitive ops: evaluate, prioritize, justify, design, propose, adapt.\n"
            "Suggested question-stem patterns:\n"
            "• CASE: <2–3 sentence scenario>. Which decision best addresses the constraints described?\n"
            "• Based on the criteria outlined in the text, which option is the most defensible choice and why?\n"
            "• If applying the framework to <new but text-consistent context>, which modification is most appropriate?\n"
            "• Which risk/assumption most critically impacts the outcome in the scenario described?\n"
            "• Which design/plan best meets the specified objectives and constraints?\n"
        )

    if extra:
        user_guidance = (
            "\nAdditional user guidance (follow without breaking the JSON schema):\n"
            f"\"\"\"\n{extra}\n\"\"\"\n"
        )
    else:
        user_guidance = ""

    return (
        level_rules
        + "\n"
        + shared_rules
        + user_guidance
        + "\nOutput ONLY the JSON object."
    )

def safe_parse_json(s: str) -> Dict[str, Any]:
    s = s.strip()
    try:
        return json.loads(s)
    except Exception:
        start, end = s.find("{"), s.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(s[start:end])
        raise ValueError("Model did not return valid JSON.")

def generate_quiz_from_text(
    content: str,
    difficulty: str,
    num_questions: int,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int = 3500,
    extra: str = "",
) -> Dict[str, Any]:
    client = get_client()
    max_chars = 14000
    content = (content or "")[:max_chars]

    full_prompt = (
        prompt_for(difficulty, num_questions, extra)
        + "\n\nUse this text as the knowledge source:\n"
        + content
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an AI quiz generator. Respond ONLY with valid JSON."},
            {"role": "user", "content": full_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    raw = resp.choices[0].message.content
    quiz = safe_parse_json(raw)

    # validation
    if "questions" not in quiz or not isinstance(quiz["questions"], list) or not quiz["questions"]:
        raise ValueError("Response JSON missing a non-empty 'questions' array.")
    for q in quiz["questions"]:
        if not all(k in q for k in ("question", "options", "answer")):
            raise ValueError("Each question needs 'question', 'options', and 'answer'.")
        if not isinstance(q["options"], list) or len(q["options"]) != 4:
            raise ValueError("Each question must have exactly 4 options.")
        if q["answer"] not in q["options"]:
            raise ValueError("Answer must be one of the options.")
    return quiz

# ---------------------------
# UI
# ---------------------------
st.set_page_config(page_title="PDF ➜ Quiz (OpenAI Direct)", page_icon="📄", layout="wide")
st.title("📄 PDF ➜ Quiz (OpenAI Direct)")
st.caption("No preview — just upload PDFs, generate MCQs with Bloom’s-based difficulty prompts.")

with st.sidebar:
    st.header("Settings")
    difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], index=0)
    num_q = st.slider("Number of questions", 1, 30, 5)
    model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o"], index=0)
    temperature = st.slider("Creativity (temperature)", 0.0, 1.0, 0.7, 0.1)
    extra = st.text_area(
        "Optional: Extra guidance",
        placeholder="e.g., emphasize practical examples; avoid trick questions; include glossary terms",
        height=100,
    )

uploaded = st.file_uploader(
    "Upload one or more PDF files",
    type=["pdf"],
    accept_multiple_files=True,
    help="You can upload multiple PDFs; they’ll be merged in order for quiz generation."
)

st.subheader("Generate Quiz")
gen = st.button("🚀 Generate Quiz", type="primary")
quiz_state_key = "pdf_openai_direct_quiz"

if gen:
    if not uploaded:
        st.warning("Please upload at least one PDF.")
    else:
        with st.spinner("Reading PDF(s) and generating your quiz..."):
            try:
                texts: List[str] = []
                for f in uploaded:
                    txt = extract_text_from_pdf(f)
                    texts.append(txt or "")
                    f.seek(0)
                merged_text = "\n\n".join(texts)
                quiz = generate_quiz_from_text(
                    content=merged_text,
                    difficulty=difficulty,
                    num_questions=num_q,
                    model=model,
                    temperature=temperature,
                    extra=extra,
                )
                st.session_state[quiz_state_key] = quiz
                st.success("Quiz generated!")
            except Exception as e:
                st.error(f"Failed to generate quiz: {e}")

# Show quiz + answer checker + download
quiz = st.session_state.get(quiz_state_key)
if quiz:
    st.divider()
    st.subheader("Your Quiz")

    answers: Dict[int, str | None] = {}
    for i, q in enumerate(quiz["questions"], start=1):
        with st.expander(f"Q{i}: {q['question']}", expanded=True):
            choice = st.radio(
                label=f"Choose an answer for Q{i}",
                options=q["options"],
                index=None,
                key=f"choice_pdf_{i}",
            )
            answers[i] = choice

    colA, colB, colC = st.columns([1, 1, 1])
    with colA:
        if st.button("✅ Check Answers"):
            correct = 0
            details = []
            for i, q in enumerate(quiz["questions"], start=1):
                chosen = answers.get(i)
                ok = (chosen == q["answer"])
                correct += int(ok)
                details.append((i, ok, q["answer"], chosen))
            st.success(f"Score: {correct} / {len(quiz['questions'])}")
            with st.expander("See details"):
                for i, ok, ans, chosen in details:
                    st.write(f"Q{i}: {'✅ Correct' if ok else '❌ Incorrect'} — Answer: **{ans}** | Your choice: **{chosen}**")

    with colB:
        if st.button("📥 Download Quiz JSON"):
            st.download_button(
                label="Download JSON",
                data=json.dumps(quiz, indent=2),
                file_name="quiz_from_pdf_openai.json",
                mime="application/json",
            )

    with colC:
        if st.button("🗑️ Clear Quiz"):
            st.session_state.pop(quiz_state_key, None)
            st.experimental_rerun()
