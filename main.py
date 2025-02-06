import streamlit as st

st.set_page_config(page_title="AI Quiz Generator", page_icon="📚")

st.title("🎉 Welcome to the AI Quiz Generator!")
st.write("Use the sidebar to navigate between different quiz generation methods.")

st.sidebar.success("Select a page above to start generating quizzes!")
important_note = """
# ***Important Note***

- 📄 When uploading the PDF, it is encouraged to choose **high-quality, text-based PDFs** rather than image-based or scanned PDFs. Our current prototype is optimized for extracting and reading text from the document.

- 📚 For better results, try uploading **one chapter at a time**. This helps the AI process the content more effectively and generate higher-quality quizzes.

- 🎉 Have fun trying out our quiz generator! If you encounter any issues or have questions, feel free to **contact me** anytime.
"""
st.markdown(important_note, unsafe_allow_html=True)