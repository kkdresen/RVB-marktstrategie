import streamlit as st
from utils import generate_response, get_variables, convert
import time
import json
import base64 
from typing import Optional
from orq_ai_sdk.models import APIError
from streamlit import _bottom
import base64

def clear_history(reset_col):
    if reset_col.button("Reset Chat", key="reset_button"):
        st.session_state.messages = []  # Clear the chat history immediately
        st.rerun()  # Force the app to rerun

def upload_file():
    """
    This function takes the uploaded file from the session, creates, and adds a list with its ID to the session (ID is later used for the deployment invoke).
    
    Param: None
    Return: None
    """
    file_uploaded_bool = st.session_state.file_uploaded
    uploaded_file = st.session_state.uploaded_file
    file_id = st.session_state.file_id

    if file_uploaded_bool:
        file_id = [convert(uploaded_file, st.session_state.get("token"))]

    st.session_state.file_id = file_id

    return

def chat_layout():
    """
    This function manages the chat section:
    - chat message text field;
    - the message history;
    - sources.
    
    Param: None
    Return: None
    """

    chat_col, reset_col = st._bottom.columns([6, 1])

    chat_input = chat_col.chat_input("Your question")

    clear_history(reset_col)

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        # Check if the message content has a type of 'text'
        for content in message["content"]:
                if content["type"] == "text":
                    with st.chat_message(message["role"]):
                        st.markdown(content["text"])

    # when message is send by user, update the parameters in case of a change
    if chat_input:
        token = st.session_state.get("token")
        key = st.session_state.get("key")
        
    try:
        # check if the token and key were given by the user to procede with the invoke
        if token and key and chat_input:
            
            if st.session_state.file_uploaded:
                upload_file()

            file_id = st.session_state.file_id

            # display the user text message
            with st.chat_message("user"):
                st.markdown(chat_input)

            # Add the user message to the chat history
            if chat_input:
                text_message = {
                    "role": "user",
                    "content": [{"type": "text", "text": chat_input}]
                }
                st.session_state.messages.append(text_message)

            # limit the number of past messages given to the model for a reference
            conv_memory = []
            response = None
            messages = st.session_state.messages

            history_num = 20 # number of maximum past messages given to the model !! CUSTOMIZE IF NEEDED !!
            if history_num < len(messages):
                slicer = len(conv_memory) - history_num
                conv_memory = messages[slicer:]
            else:
                conv_memory = messages

            # display the response and a source from a model
            with st.chat_message("assistant"):
                try:
                    response, sources = generate_response(api_token = token, key_input = key, conv_memory= conv_memory , variable_dict = None, context_input = None, file_id = file_id)

                    st.markdown(response)

                    if sources:
                        with st.expander(label= "Sources", expanded=False, icon="📖"):
                            counter = 0
                            for source in sources:
                                counter += 1
                                file_name = source["file_name"]
                                page_number = source["page_number"]
                                chunk_text = source["chunk"]
                                st.markdown(f"**{counter}. {file_name} - page {int(page_number)}:**")
                                st.markdown(chunk_text) 

                    # Append the model response in the message history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": [{"type": "text", "text": response}]
                    })

                except APIError as e:
                    error_dict = json.loads(e.body)
                    st.info(error_dict["error"])
                    # pass

                except Exception as e:
                    print(e)
                    # pass

        else:
            st.info('Please provide all the necessary parameters')

    except Exception as e:
        print(e)
        # pass

    return



def show():
    token = None
    Key = None

    correct_token = False

    with st.sidebar:

        token = st.text_input(
            "Access token",
            label_visibility="visible",
            disabled=False,
            placeholder="Access token"
        )

        if token:
            st.session_state["token"] = token
            key = st.session_state.get("key")

            try:
                variables = list(get_variables(token, key))
                correct_token = True

                # display the file uploader
                uploaded_file = st.file_uploader("Additional Material", type=["pdf", "txt", "docx", "csv", "xls"], accept_multiple_files=False)

                # update the uploaded files in the session
                if st.session_state.uploaded_file != uploaded_file:
                    st.session_state.uploaded_file = uploaded_file
                
                if uploaded_file:
                    st.session_state.file_uploaded = True
            
            except APIError as e:
                st.info('Please verify if this token has an access to "ACSW Demos" workspace')

    if token and key and correct_token:
        chat_layout()
