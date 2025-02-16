import streamlit as st
import openai
from PyPDF2 import PdfReader
import json

# Load the OpenAI API key from environment variables
import os
from dotenv import load_dotenv


load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


def extract_text_from_pdf(pdf_file):
    """Extract text from a PDF file."""
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def generate_quiz(content, difficulty, num_questions):
    """Generate quiz questions using OpenAI API."""
    max_content_length = 5000  # Limit content length
    content = content[:max_content_length]

    prompt = "";
    if difficulty.lower() == "easy":
        prompt = (
            f"Generate {num_questions} multiple-choice questions that assess lower levels of Bloom's Taxonomy: Remembering and Understanding. "
            f"These questions should focus on factual recall, definitions, basic principles, and fundamental concepts. "
            f"Ensure that questions are clear, direct, and test theoretical knowledge without requiring deep analysis. "
            f"Examples of question styles include:\n"
            f"- 'Which of the following best defines [concept]?' \n"
            f"- 'What is the primary function of [topic]?' \n"
            f"- 'Which statement about [subject] is correct?' \n"
            f"Use the following content as the knowledge source:\n{content}\n"
            f"Output only a JSON object with this structure:\n"
            f"{{\"questions\":[{{\"question\":\"<question_text>\", \"options\":[\"option1\",\"option2\",\"option3\",\"option4\"], \"answer\":\"correct_option\"}}]}}"
        )

    elif difficulty.lower() == "medium":
        prompt = (
            f"Generate {num_questions} multiple-choice questions that assess middle levels of Bloom's Taxonomy: Applying and Analyzing. "
            f"These questions should require students to apply concepts to real-world scenarios and analyze relationships between different ideas. "
            f"Ensure that questions involve case studies, problem-solving, and comparative analysis. "
            f"Examples of question styles include:\n"
            f"- 'If [scenario] occurs, which principle of [topic] should be applied to solve it?' \n"
            f"- 'How does [concept A] differ from [concept B] in practical use?' \n"
            f"- 'Which of the following best explains why [phenomenon] happens?' \n"
            f"Use the following content as the knowledge source:\n{content}\n"
            f"Output only a JSON object with this structure:\n"
            f"{{\"questions\":[{{\"question\":\"<question_text>\", \"options\":[\"option1\",\"option2\",\"option3\",\"option4\"], \"answer\":\"correct_option\"}}]}}"
        )

    elif difficulty.lower() == "hard":
        prompt = (
            f"Generate {num_questions} multiple-choice questions that assess upper levels of Bloom's Taxonomy: Evaluating and Creating. "
            f"These questions should require critical thinking, evaluation of theories, synthesis of new ideas, and justification of arguments. "
            f"Ensure that questions involve critical assessment, theoretical comparison, and decision-making based on incomplete or conflicting information. "
            f"Examples of question styles include:\n"
            f"- 'Which of the following arguments best supports [theory] in the context of [situation]?' \n"
            f"- 'If you were to design a new [system/method], which factors would be most critical for its success?' \n"
            f"- 'Evaluate the strengths and weaknesses of [approach A] versus [approach B] in solving [problem].' \n"
            f"Use the following content as the knowledge source:\n{content}\n"
            f"Output only a JSON object with this structure:\n"
            f"{{\"questions\":[{{\"question\":\"<question_text>\", \"options\":[\"option1\",\"option2\",\"option3\",\"option4\"], \"answer\":\"correct_option\"}}]}}"
        )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an AI quiz generator for university level students that can provide quizzes according to Bloom's Taxonomy."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3000
        )
        raw_response = response.choices[0].message['content'].strip()
        # Extract JSON from response
        json_start = raw_response.find("{")
        json_end = raw_response.rfind("}") + 1
        valid_json = raw_response[json_start:json_end]
        #st.write("Raw API Response for Debugging:", raw_response)
        return json.loads(valid_json)
    except json.JSONDecodeError:
        st.error("Too many questions please reduce the number of questions.")
        return None
    except Exception as e:
        st.error(f"Error generating quiz: {e}")
        return None

def run():
    st.title("Interactive Quiz Generator")


    # Initialize session state
    if "quiz" not in st.session_state:
        st.session_state.quiz = None
    if "answers" not in st.session_state:
        st.session_state.answers = {}

    # File upload
    pdf_file = st.file_uploader("Upload a PDF file", type=["pdf"])

    # Quiz options
    difficulty_pdf = st.selectbox("Select Difficulty", ["easy", "medium", "hard"], key="difficulty_quiz_pdf")

    num_questions_pdf = st.number_input("Number of Questions", min_value=1, max_value=50, value=5, key="num_q_pdf")

    if st.button("Generate Quiz", key="generate_quiz_pdf"):
        if not pdf_file:
            st.error("Please upload a PDF file.")
        else:
            with st.spinner("Extracting text from PDF and generating quiz..."):
                pdf_text = extract_text_from_pdf(pdf_file)
                st.session_state.quiz = generate_quiz(pdf_text, difficulty_pdf, num_questions_pdf)
                st.session_state.answers = {}  # Reset answers

    if st.session_state.quiz:
        st.success("Quiz generated successfully!")

        for idx, question in enumerate(st.session_state.quiz.get("questions", []), start=1):
            st.write(f"**Question {idx}:** {question['question']}")
            options = question['options']

            # Persist user's answer in session state
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