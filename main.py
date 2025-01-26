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
    max_content_length = 2000  # Limit content length
    content = content[:max_content_length]

    prompt = (
        f"Generate {num_questions} {difficulty} multiple-choice questions based on the following content:\n{content}\n"
        f"Provide the output as a JSON object with the following structure: \n"
        "{\"questions\":[{\"question\":\"<question_text>\", \"options\":[\"option1\",\"option2\",\"option3\",\"option4\"], \"answer\":\"correct_option\"}]}"
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        raw_response = response.choices[0].message['content'].strip()
        return json.loads(raw_response)
    except json.JSONDecodeError:
        st.error("Error: The API response could not be parsed as JSON.")
        return None
    except Exception as e:
        st.error(f"Error generating quiz: {e}")
        return None

def main():
    st.title("Interactive Quiz Generator")

    # Initialize session state
    if "quiz" not in st.session_state:
        st.session_state.quiz = None
    if "answers" not in st.session_state:
        st.session_state.answers = {}

    # File upload
    pdf_file = st.file_uploader("Upload a PDF file", type=["pdf"])

    # Quiz options
    difficulty = st.selectbox("Select Difficulty", ["easy", "medium", "hard"])
    num_questions = st.number_input("Number of Questions", min_value=1, max_value=50, value=5)

    if st.button("Generate Quiz"):
        if not pdf_file:
            st.error("Please upload a PDF file.")
        else:
            with st.spinner("Extracting text from PDF and generating quiz..."):
                pdf_text = extract_text_from_pdf(pdf_file)
                st.session_state.quiz = generate_quiz(pdf_text, difficulty, num_questions)
                st.session_state.answers = {}  # Reset answers

    if st.session_state.quiz:
        st.success("Quiz generated successfully!")

        for idx, question in enumerate(st.session_state.quiz.get("questions", []), start=1):
            st.write(f"**Question {idx}:** {question['question']}")
            options = question['options']

            # Persist user's answer in session state
            st.session_state.answers[f"q{idx}"] = st.radio(
                f" Select your answer for Question {idx}", options, key=f"q{idx}", index= None
            )

        if st.button("Submit All Answers"):
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

if __name__ == "__main__":
    main()