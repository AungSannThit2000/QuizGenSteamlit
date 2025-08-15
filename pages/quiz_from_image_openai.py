# pages/02_Image_Quiz_OpenAI.py
# ------------------------------------------------------------
# One-file Streamlit page that:
# - Uploads one or more images
# - Sends them DIRECTLY to OpenAI (vision input)
# - Returns a validated MCQ quiz JSON
# - Lets you review, check answers, and download JSON
#
# Setup:
#   pip install streamlit openai python-dotenv
#   export OPENAI_API_KEY=sk-...     # or set in .env
# Run:
#   streamlit run imagetoQuiz.py
#   (This page will appear in the sidebar under "Pages")
# ------------------------------------------------------------

from __future__ import annotations
import os, json, base64, mimetypes
from typing import List, Union, Dict, Any

import streamlit as st

# Optional .env support for local testing
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# OpenAI SDK v1
from openai import OpenAI

# ---------------------------
# Configuration & Utilities
# ---------------------------
st.set_page_config(page_title="Image ➜ Quiz (OpenAI Direct)", page_icon="🖼️", layout="wide")

def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.stop()  # halts Streamlit execution with a nice message
        raise RuntimeError("Missing OPENAI_API_KEY in environment.")
    return OpenAI(api_key=api_key)

ImageInput = Union[str, bytes, bytearray]

def _guess_mime(path: str | None) -> str:
    if not path:
        return "image/png"
    mt, _ = mimetypes.guess_type(path)
    return mt or "image/png"

def _to_data_uri(img: ImageInput) -> str:
    """Accept file path or raw bytes and return a base64 data URI."""
    if isinstance(img, (bytes, bytearray)):
        b64 = base64.b64encode(img).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    elif isinstance(img, str):
        with open(img, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{_guess_mime(img)};base64,{b64}"
    else:
        raise TypeError("image must be a path (str) or bytes-like object")

def prompt_for(difficulty: str, n: int) -> str:
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


    return (
        level_rules
        + "\n"
        + shared_rules
        + "\nOutput ONLY the JSON object."
    )


def _safe_parse_json(s: str) -> Dict[str, Any]:
    s = s.strip()
    try:
        return json.loads(s)
    except Exception:
        # Try to salvage if the model returned extra characters
        start, end = s.find("{"), s.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(s[start:end])
        raise ValueError("Model did not return valid JSON.")

def generate_quiz_from_images(
    images: List[ImageInput],
    difficulty: str = "easy",
    num_questions: int = 5,
    model: str = "gpt-4o-mini",
    temperature: float = 0.6,
    max_tokens: int = 2000,
) -> Dict[str, Any]:
    client = get_client()
    num_questions = max(1, min(int(num_questions), 50))

    content_blocks = [{"type": "text", "text": prompt_for(difficulty, num_questions)}]
    for img in images:
        content_blocks.append({"type": "image_url", "image_url": {"url": _to_data_uri(img)}})

    messages = [
        {
            "role": "system",
            "content": (
                "You are an AI quiz generator for students. "
                "Look at the provided image(s) and produce ONLY valid JSON. "
                "Do not include commentary, markdown, or code fences."
            ),
        },
        {"role": "user", "content": content_blocks},
    ]

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = resp.choices[0].message.content
    quiz = _safe_parse_json(content)

    # Validate basic structure
    if "questions" not in quiz or not isinstance(quiz["questions"], list) or not quiz["questions"]:
        raise ValueError("Response JSON missing non-empty 'questions' array.")
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
st.title("🖼️ Image ➜ Quiz (OpenAI Direct)")
st.caption("Uploads go straight to OpenAI’s vision model (no external OCR). For testing/prototyping only.")

with st.sidebar:
    st.header("Settings")
    difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], index=0)
    num_q = st.slider("Number of questions", 1, 20, 5)
    model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o"], index=0)
    temperature = st.slider("Creativity (temperature)", 0.0, 1.0, 0.6, 0.1)

uploaded = st.file_uploader(
    "Upload one or more images",
    accept_multiple_files=True,
    type=["png", "jpg", "jpeg", "webp"],
    help="You can upload multiple images; they'll be processed together."
)

# Preview
st.subheader("Preview")
if uploaded:
    for f in uploaded:
        st.image(f, caption=f.name, use_container_width=True)
else:
    st.info("Upload images to preview them here.")

st.subheader("Generate Quiz")
quiz_state_key = "openai_direct_quiz_state"
gen = st.button("🚀 Generate Quiz", type="primary")
if gen:
    if not uploaded:
        st.warning("Please upload at least one image.")
    else:
        with st.spinner("Thinking from image(s) and building your quiz..."):
            images_bytes = [f.getvalue() for f in uploaded]
            try:
                quiz = generate_quiz_from_images(
                    images=images_bytes,
                    difficulty=difficulty,
                    num_questions=num_q,
                    model=model,
                    temperature=temperature,
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
                key=f"choice_{i}",
                horizontal=False,
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
                file_name="quiz_from_image_openai.json",
                mime="application/json",
            )

    with colC:
        if st.button("🗑️ Clear Quiz"):
            st.session_state.pop(quiz_state_key, None)
            st.experimental_rerun()
