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


def variable_textfields(variables):
    """
    This function creates a text fields for every variable in the given deployment and places user input, from text fields,
    in the session with a corresponding key.
    
    Param: A list of variables
    Return: None
    """
    if len(variables)>0:
        st.markdown("<p style='font-weight: normal; font-size: 14px;'>Subject</p>", unsafe_allow_html=True)
    
    # creating a text field for every variable in the given deployment
    for index, variable in enumerate(variables):

        variable_input = st.text_input(
            "variable",
            label_visibility="collapsed",
            disabled=False,
            placeholder=f"{variable.replace("_"," ").capitalize()}",
            key=f"variable_key_{index}" # setting unique key due to streamlit rules
        )

        if variable_input:
            st.session_state.variable_dict[variable]=variable_input
        
    return

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


def image_uploader():
    """
    This function displays an image uploader, enclodes the uploaded immage with base 64 encoding, and adds it to the session in the URI format
    
    Param: None
    Return: None
    """
    st.markdown("<p style='font-weight: normal; font-size: 14px;'>Student Answers</p>", unsafe_allow_html=True)

    # Accept a single file
    image = st.file_uploader("Upload an image", type=["PNG", "JPG", "JPEG"], label_visibility="collapsed", accept_multiple_files=False)

    if image:
        base64_string = base64.b64encode(image.read()).decode('utf-8')
        data_uri = f"data:{image.type};base64,{base64_string}"
    
        st.session_state.uploaded_image = data_uri

    return


def chat_layout(variables):
    """
    This function manages the chat section:
    - chat message text field;
    - the message history;
    - the input from the image uploader;
    - sources.
    
    Param: A list of variables
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
        variable_dict = st.session_state.variable_dict
        image = st.session_state.get("uploaded_image")
        
    try:
        # check if the token, key and all variables were given by the user to procede with the invoke
        if token and key and chat_input and (len(variables) == len(variable_dict)):
            
            if st.session_state.file_uploaded:
                upload_file()

            file_id = st.session_state.file_id

            # display the user text message
            with st.chat_message("user"):
                st.markdown(chat_input)


            image_message = None

            # Add the user message to the chat history
            if chat_input:
                text_message = {
                    "role": "user",
                    "content": [{"type": "text", "text": chat_input}]
                }
                st.session_state.messages.append(text_message)

                # Append the uploaded image as a separate message
                if image:
                    image_message = {
                        "role": "user",
                        "content": [{"type": "image_url", "image_url": { "url": image}}]
                    }
                    del st.session_state["uploaded_image"]

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

            if image_message:
                conv_memory.append(image_message)

            # display the response and a source from a model
            with st.chat_message("assistant"):
                try:
                    response, sources = generate_response(api_token = token, key_input = key, conv_memory= conv_memory , variable_dict = variable_dict, context_input = None, file_id = file_id)

                    st.markdown(response)

                    if sources:
                        with st.expander(label= "Sources", expanded=False, icon="📖"):
                            counter = 0
                            for source in sources:
                                counter += 1
                                file_name = source["file_name"]
                                page_number = source["page_number"]
                                chunk_text = source["chunk"]
                                st.markdown(f"**{counter}. {file_name} - page {page_number}:**")
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
    variables = None

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
                variable_textfields(variables)

                # display the file uploader
                uploaded_file = st.file_uploader('Exam Questions',type=["pdf", "txt", "docx", "csv", "xls"], accept_multiple_files=False)

                # update the uploaded files in the session
                if st.session_state.uploaded_file != uploaded_file:
                    st.session_state.uploaded_file = uploaded_file
        
                if uploaded_file:
                    st.session_state.file_uploaded = True

                image_uploader()

            except APIError as e:
                    print(e)
                    # st.info(e)
                    st.info('Please verify if this token has an access to "ACSW Demos" workspace')
    
    if variables:
        chat_layout(variables) 
