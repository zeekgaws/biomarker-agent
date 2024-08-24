import streamlit as st
import streamlit.components.v1 as components

import pandas as pd
import numpy as np
import util.bedrock
from argparse import ArgumentParser




bedrock = util.BedrockAgent("SQL agent")

st.set_page_config(layout="wide", page_title="SQL Agent")

st.title("SQL Query Agent")
heading_column1, heading_column_space, heading_column2 = st.columns((6, 2, 2))

with heading_column1:
    st.subheader(":grey[Amazon Bedrock Agents]")

with heading_column2:
    st.link_button(
        "_Github_ :sunglasses:",
        "https://quip-amazon.com/d7avAHNyd5yu/Accelerate-analysis-and-discovery-of-cancer-biomarkers-with-Agents-for-Bedrock",
    )

st.markdown(
    """
<style>
    .stButton button {
        background-color: white;
        width: 82px;
        border: 0px;
        padding: 0px;
    }
    .stButton button:hover {
        background-color: white;
        color: black;
    }

</style>
""",
    unsafe_allow_html=True,
)

if "chat_history" not in st.session_state or len(st.session_state["chat_history"]) == 0:
    st.session_state["chat_history"] = [
        {
            "role": "assistant",
            "prompt": "Hello I am a SQL query agent how may I help you",
        }
    ]


for index, chat in enumerate(st.session_state["chat_history"]):
    with st.chat_message(chat["role"]):
        if index == 0:
            col1, space, col2 = st.columns((7, 1, 2))
            col1.markdown(chat["prompt"])

            if col2.button("Clear", type="secondary"):
                st.session_state["chat_history"] = []
                bedrock.new_session()
                st.rerun()

        elif chat["role"] == "assistant":
            col1, col2, col3 = st.columns((5, 4, 1))

            col1.markdown(chat["prompt"], unsafe_allow_html=True)

            if col3.checkbox(
                "Trace", value=False, key=index, label_visibility="visible"
            ):
                col2.subheader("Trace")
                col2.markdown(chat["trace"])
        else:
            st.markdown(chat["prompt"])

if prompt := st.chat_input("Ask the bot a question..."):
    st.session_state["chat_history"].append({"role": "human", "prompt": prompt})

    with st.chat_message("human"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        col1, col2, col3 = st.columns((5, 4, 1))

        if col3.checkbox(
            "Trace",
            value=True,
            key=len(st.session_state["chat_history"]),
            label_visibility="visible",
        ):
            col2.subheader("Trace")

        response_text, trace_text = bedrock.invoke_agent(prompt, col2)
        st.session_state["chat_history"].append(
            {"role": "assistant", "prompt": response_text, "trace": trace_text}
        )

        col1.markdown(response_text, unsafe_allow_html=True)
        # if col3.checkbox('Trace', key=len(st.session_state["chat_history"]), label_visibility="hidden"):
        # col2.markdown(trace_text)
