import streamlit as st
import os
from PIL import Image
import warnings
import requests
import base64
import json
from dotenv import load_dotenv
import openai

warnings.simplefilter(action='ignore', category=FutureWarning)

# **SECURITY WARNING:** Do NOT hardcode your API key directly in your code,
# especially if you plan to share it or put it in a public repository.
# Instead, store it as an environment variable.
load_dotenv()
API_KEY = os.getenv("GOOGLE_CLOUD_VISION_API_KEY")  # Get from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")


if not API_KEY:
    st.error("API key not found. Set the GOOGLE_CLOUD_VISION_API_KEY environment variable.")
    st.stop()  # Stop execution if the API key is missing

ocr_string = ""
st.title("Upload photos to create quizzes from them!")
def generate_quiz(content, difficulty, num_questions):
    """Generate quiz questions using OpenAI API."""
    max_content_length = 5000  # Limit content length
    content = content[:max_content_length]
    prompt = "";
    if difficulty.lower() == "easy":
        st.write("easy difficulty")
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
        st.write("medium difficulty")
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
        st.write("hard difficulty")
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

uploaded_files = st.file_uploader("Upload images", accept_multiple_files=True)

if uploaded_files is not None:
    for uploaded_file in uploaded_files:
        file_bytes = uploaded_file.read()
        encoded_string = base64.b64encode(file_bytes).decode("utf-8")

        url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
        headers = {"Content-Type": "application/json"}
        data = {
            "requests": [
                {
                    "image": {"content": encoded_string},
                    "features": [{"type": "TEXT_DETECTION"}]  # Or other features
                }
            ]
        }

        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            try:
                response_json = response.json()
                if response_json['responses'][0].get('fullTextAnnotation'): #Check if text is detected
                    annotations = response_json['responses'][0]['fullTextAnnotation']['text']
                    ocr_string += annotations + "\n"
                else:
                     ocr_string += "No text detected in this image.\n"
                     st.warning(f"No text detected in {uploaded_file.name}. Please try again with a clearer image.")
            except (KeyError, IndexError, json.JSONDecodeError) as e: #Catch potential errors with the API response
                st.error(f"Error processing API response: {e}")
                st.write(response.text) #Print the raw response for debugging
        else:
            st.error(f"API request failed: {response.status_code}")
            st.write(response.text) #Print the raw response for debugging



if "quiz_image" not in st.session_state:
    st.session_state.quiz_image = None
if "answers_image" not in st.session_state:
    st.session_state.answers_image = {}

difficulty_image = st.selectbox("Select Difficulty", ["easy", "medium", "hard"], key="difficulty_quiz_image")
num_questions_image = st.number_input("Number of Questions", min_value=1, max_value=50, value=5, key="num_q_image")
if st.button("Generate Quiz", key="generate_quiz_image"):
    with st.spinner("Extracting text from Image and generating quiz..."):
        st.session_state.quiz_image = generate_quiz(ocr_string, difficulty_image, num_questions_image)
        st.session_state.answers_image = {}  # Reset answers
        

st.subheader("Answer Quiz here!", divider='violet')
if st.session_state.quiz_image:
    st.success("Quiz generated successfully!")
    for idx, question in enumerate(st.session_state.quiz_image.get("questions", []), start=1):
        st.write(f"**Question {idx}:** {question['question']}")
        options = question['options']

        # Persist user's answer in session state
        st.session_state.answers_image[f"q{idx}"] = st.radio(
            f"Select your answer for Question {idx}", options, key=f"q{idx}", index=None
        )

    if st.button("Submit All Answers", key="submit_answers_image"):
        correct_count = 0
        for idx, question in enumerate(st.session_state.quiz_image.get("questions", []), start=1):
            user_answer = st.session_state.answers_image.get(f"q{idx}")
            correct_answer = question['answer']
            if user_answer == correct_answer:
                st.success(f"Question {idx}: Correct!")
                correct_count += 1
            else:
                st.error(f"Question {idx}: Incorrect. The correct answer is: {correct_answer}")
        st.write(f"**You got {correct_count}/{len(st.session_state.quiz_image.get('questions', []))} correct!**")
