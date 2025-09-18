import streamlit as st
from openai import OpenAI
from coderag.config import OPENAI_API_KEY, OPENAI_CHAT_MODEL
from coderag.summary import get_project_summary
from prompt_flow import execute_rag_flow

# Initialize the OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://api2.road2all.com/v1")

st.title("RepoRAG: Understand Your Repository")


# Display project summary
project_summary = get_project_summary()
with st.expander("📄 Project Summary", expanded=True):
    st.markdown(project_summary)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("What is your coding question?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        try:
            response = execute_rag_flow(prompt)
            message_placeholder.markdown(response)
            full_response = response
        except Exception as e:
            error_message = f"Error in RAG flow execution: {str(e)}"
            st.error(error_message)
            full_response = error_message

    st.session_state.messages.append({"role": "assistant", "content": full_response})