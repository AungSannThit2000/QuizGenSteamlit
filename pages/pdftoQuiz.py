import streamlit as st
import openai
from PyPDF2 import PdfReader
import json
from datetime import datetime
import os
import re
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def sanitize_user_prompt(user_input):
    """Basic sanitization to prevent prompt injection."""
    if not user_input:
        return ""
    injection_phrases = [
        r"(?i)you are an", r"(?i)ignore previous", r"(?i)act as", r"(?i)disregard",
        r"(?i)system:", r"(?i)user:", r"(?i)assistant:"
    ]
    for phrase in injection_phrases:
        user_input = re.sub(phrase, "", user_input)
    return user_input.strip()

def save_generated_quiz_log(prompt, quiz_data, difficulty, num_questions):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "difficulty": difficulty,
        "num_questions": num_questions,
        "prompt_used": prompt,
        "quiz": quiz_data
    }

    filename = f"quiz_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(log_entry, f, indent=2)

    return filename

def generate_quiz(content, difficulty, num_questions, user_addition=""):
    max_content_length = 5000
    content = content[:max_content_length]

    base_prompt = ""
    if difficulty.lower() == "easy":
        base_prompt = (
            f"Generate {num_questions} multiple-choice questions that assess lower levels of Bloom's Taxonomy: Remembering and Understanding. "
            f"These questions should focus on factual recall, definitions, basic principles, and fundamental concepts. "
            f"Ensure that questions are clear, direct, and test theoretical knowledge without requiring deep analysis. "
            f"Examples of question styles include:\n"
            f"- 'Which of the following best defines [concept]?' \n"
            f"- 'What is the primary function of [topic]?' \n"
            f"- 'Which statement about [subject] is correct?'"
        )
    elif difficulty.lower() == "medium":
        base_prompt = (
            f"Generate {num_questions} multiple-choice questions that assess middle levels of Bloom's Taxonomy: Applying and Analyzing. "
            f"These questions should require students to apply concepts to real-world scenarios and analyze relationships between different ideas. "
            f"Ensure that questions involve case studies, problem-solving, and comparative analysis. "
            f"Examples of question styles include:\n"
            f"- 'If [scenario] occurs, which principle of [topic] should be applied to solve it?' \n"
            f"- 'How does [concept A] differ from [concept B] in practical use?' \n"
            f"- 'Which of the following best explains why [phenomenon] happens?'"
        )
    elif difficulty.lower() == "hard":
        base_prompt = (
            f"Generate {num_questions} multiple-choice questions that assess upper levels of Bloom's Taxonomy: Evaluating and Creating. "
            f"These questions should require critical thinking, evaluation of theories, synthesis of new ideas, and justification of arguments. "
            f"Ensure that questions involve critical assessment, theoretical comparison, and decision-making based on incomplete or conflicting information. "
            f"Examples of question styles include:\n"
            f"- 'Which of the following arguments best supports [theory] in the context of [situation]?' \n"
            f"- 'If you were to design a new [system/method], which factors would be most critical for its success?' \n"
            f"- 'Evaluate the strengths and weaknesses of [approach A] versus [approach B] in solving [problem].'"
        )

    # Sanitize and include user additions at the start
    sanitized = sanitize_user_prompt(user_addition)
    if sanitized:
        base_prompt += (
            f"\n\nIMPORTANT: The user has added specific instructions to guide question creation. "
            f"Please include these ideas in the quiz generation while preserving the structure and taxonomy level:\n"
            f"\"\"\"\n{sanitized}\n\"\"\""
        )

    # Now add the content after that
    full_prompt = (
        f"{base_prompt}\n\nUse the following content as the knowledge source:\n{content}\n\n"
        f"Output only a JSON object with this structure:\n"
        f"{{\"questions\":[{{\"question\":\"<question_text>\", \"options\":[\"option1\",\"option2\",\"option3\",\"option4\"], \"answer\":\"correct_option\"}}]}}"
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an AI quiz generator for university level students that can provide quizzes according to Bloom's Taxonomy."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.7,
            max_tokens=3000
        )
        raw_response = response.choices[0].message['content'].strip()
        json_start = raw_response.find("{")
        json_end = raw_response.rfind("}") + 1
        valid_json = raw_response[json_start:json_end]
        return json.loads(valid_json), full_prompt
    except json.JSONDecodeError:
        st.error("Too many questions, please reduce the number.")
        return None, None
    except Exception as e:
        st.error(f"Error generating quiz: {e}")
        return None, None

def run():
    st.title("Interactive Quiz Generator")

    if "quiz" not in st.session_state:
        st.session_state.quiz = None
    if "answers" not in st.session_state:
        st.session_state.answers = {}
    if "log_filename" not in st.session_state:
        st.session_state.log_filename = None

    pdf_file = st.file_uploader("Upload a PDF file", type=["pdf"])
    difficulty_pdf = st.selectbox("Select Difficulty", ["easy", "medium", "hard"], key="difficulty_quiz_pdf")
    num_questions_pdf = st.number_input("Number of Questions", min_value=1, max_value=50, value=5, key="num_q_pdf")

    user_custom_prompt = st.text_area(
        "Optional: Add extra instruction for the AI (e.g., 'focus on real-life examples', 'avoid trick questions')",
        placeholder="Leave empty if no extra instructions"
    )

    if st.button("Generate Quiz", key="generate_quiz_pdf"):
        if not pdf_file:
            st.error("Please upload a PDF file.")
        else:
            with st.spinner("Extracting text from PDF and generating quiz..."):
                pdf_text = extract_text_from_pdf(pdf_file)
                quiz_data, used_prompt = generate_quiz(
                    pdf_text,
                    difficulty_pdf,
                    num_questions_pdf,
                    user_addition=user_custom_prompt
                )

                if quiz_data:
                    st.session_state.quiz = quiz_data
                    st.session_state.answers = {}

                    log_filename = save_generated_quiz_log(
                        prompt=used_prompt,
                        quiz_data=quiz_data,
                        difficulty=difficulty_pdf,
                        num_questions=num_questions_pdf
                    )
                    st.session_state.log_filename = log_filename

    if st.session_state.quiz:
        st.success("Quiz generated successfully!")

        if st.session_state.log_filename:
            with open(st.session_state.log_filename, "rb") as f:
                st.download_button(
                    label="📥 Download Quiz Log (JSON)",
                    data=f,
                    file_name=st.session_state.log_filename,
                    mime="application/json"
                )

        for idx, question in enumerate(st.session_state.quiz.get("questions", []), start=1):
            st.write(f"**Question {idx}:** {question['question']}")
            options = question['options']

            st.session_state.answers[f"q{idx}"] = st.radio(
                f"Select your answer for Question {idx}", options, key=f"q{idx}", index=None
            )

        if st.button("Submit All Answers", key="submit_answers_pdf"):
            correct_count = 0
            for idx, question in enumerate(st.session_state.quiz.get("questions", []), start=1):
                user_answer = st.session_state.answers.get(f"q{idx}")
                correct_answer = question['answer']
                if user_answer == correct_answer:
                    st.success(f"Question {idx}: Correct!")
                    correct_count += 1
                else:
                    st.error(f"Question {idx}: Incorrect. The correct answer is: {correct_answer}")
            st.write(f"**You got {correct_count}/{len(st.session_state.quiz.get('questions', []))} correct!**")

run()
