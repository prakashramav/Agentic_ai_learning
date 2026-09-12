import streamlit as st
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain.tools import tool
from dotenv import load_dotenv
import fitz  # PyMuPDF
import re


# CONFIGURATION

load_dotenv()

OLLAMA_MODEL = "llama3.1:8b"


# OLLAMA LLM

llm = ChatOllama(
    model=OLLAMA_MODEL,
    temperature=0
)


# APPLICATION INFORMATION

if "application_info" not in st.session_state:
    st.session_state.application_info = {
        "name": None,
        "email": None,
        "skills": None
    }


# EXTRACT APPLICATION INFORMATION

def extract_application_info(text: str):

    application_info = st.session_state.application_info

    # Extract Email

    email_match = re.search(
        r"\b[\w\.-]+@[\w\.-]+\.\w+\b",
        text
    )

    if email_match:
        application_info["email"] = email_match.group(0).strip()


    # Extract Name

    name_patterns = [
        r"(?:my name is|i am|i'm)\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,3})",
        r"(?:name)\s*[:\-]\s*([A-Za-z]+(?:\s+[A-Za-z]+){0,3})"
    ]

    for pattern in name_patterns:

        name_match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if name_match:

            name = name_match.group(1).strip()

            invalid_names = [
                "a",
                "an",
                "from",
                "using",
                "looking",
                "interested"
            ]

            if name.lower() not in invalid_names:

                application_info["name"] = name.title()

                break


    # Extract Skills

    skills_patterns = [
        r"(?:skills are|my skills are|skills:)\s*(.+)",
        r"(?:i know|i can use|i work with)\s+(.+)"
    ]

    for pattern in skills_patterns:

        skills_match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if skills_match:

            skills = skills_match.group(1).strip()

            application_info["skills"] = skills

            break


# EXTRACT TEXT FROM PDF

def extract_text_from_pdf(uploaded_file):

    pdf_bytes = uploaded_file.getvalue()

    doc = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    text = ""

    for page in doc:
        text += page.get_text()

    doc.close()

    return text


# EXTRACT TEXT FROM TXT

def extract_text_from_txt(uploaded_file):

    return uploaded_file.getvalue().decode(
        "utf-8",
        errors="ignore"
    )


# EXTRACT INFORMATION FROM CV

def extract_info_from_cv(text: str):

    extracted_info = {
        "name": None,
        "email": None,
        "skills": None
    }

    # Email

    email_match = re.search(
        r"\b[\w\.-]+@[\w\.-]+\.\w+\b",
        text
    )

    if email_match:

        extracted_info["email"] = (
            email_match.group(0).strip()
        )


    # Name

    name_patterns = [

        r"(?:Full Name|Name)\s*[:\-]\s*([A-Za-z]+(?:\s+[A-Za-z]+){0,3})",

        r"(?:Resume of|CV of)\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,3})"

    ]

    for pattern in name_patterns:

        name_match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if name_match:

            extracted_info["name"] = (
                name_match.group(1).strip()
            )

            break


    # Skills

    skills_match = re.search(
        r"Skills\s*[:\-]?\s*(.*?)(?=\n\s*(?:Projects|Experience|Education|Certifications|Achievements|$))",
        text,
        re.IGNORECASE | re.DOTALL
    )

    if skills_match:

        skills = skills_match.group(1)

        skills = skills.replace(
            "\u2022",
            ""
        )

        skills = skills.replace(
            "\n",
            ", "
        )

        skills = skills.replace(
            " - ",
            ", "
        )

        skills = re.sub(
            r"\s+",
            " ",
            skills
        )

        extracted_info["skills"] = (
            skills.strip(" ,")
        )


    return extracted_info


# CHECK APPLICATION GOAL

def check_application_goal():

    application_info = st.session_state.application_info

    missing = [
        key
        for key, value in application_info.items()
        if not value
    ]

    if not missing:

        return (
            "READY",
            "All required information has been collected."
        )

    return (
        "INCOMPLETE",
        missing
    )


# LANGCHAIN TOOLS

@tool
def check_application_status() -> str:
    """
    Check whether the user's name, email and skills
    have been collected.
    """

    status, data = check_application_goal()

    if status == "READY":

        info = st.session_state.application_info

        return (
            f"Application is complete. "
            f"Name: {info['name']}. "
            f"Email: {info['email']}. "
            f"Skills: {info['skills']}."
        )

    return (
        "Application is incomplete. "
        f"Missing information: {', '.join(data)}."
    )


@tool
def get_application_information() -> str:
    """
    Return the currently collected application information.
    """

    info = st.session_state.application_info

    return (
        f"Name: {info['name']}\n"
        f"Email: {info['email']}\n"
        f"Skills: {info['skills']}"
    )


# CREATE LANGCHAIN AGENT

tools = [
    check_application_status,
    get_application_information
]


agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt="""
You are a helpful Job Application Assistant.

Your job is to help the user complete a job application.

The required information is:

1. Name
2. Email
3. Skills

Be conversational and concise.

If some information is missing, politely ask the user
for the missing information.

If all information is available, tell the user that
their application information is complete.

Do not invent information.
Do not change information supplied by the user.
"""
)


# STREAMLIT PAGE CONFIG

st.set_page_config(
    page_title="Job Application Assistant",
    page_icon="🎯",
    layout="centered"
)


# TITLE

st.title("🧠 Goal-Based Job Application Agent")

st.markdown(
    """
Tell me your **name**, **email**, and **skills**.

You can also upload your resume and I will try to
extract the information automatically.
"""
)


# SESSION STATE

if "chat_history" not in st.session_state:

    st.session_state.chat_history = []


if "goal_complete" not in st.session_state:

    st.session_state.goal_complete = False


if "application_summary" not in st.session_state:

    st.session_state.application_summary = ""


# SIDEBAR

st.sidebar.header("📤 Upload Resume")

resume = st.sidebar.file_uploader(
    "Upload your resume",
    type=["pdf", "txt"]
)


# PROCESS RESUME

if resume:

    st.sidebar.success(
        "Resume uploaded successfully!"
    )

    if resume.type == "application/pdf":

        resume_text = extract_text_from_pdf(
            resume
        )

    else:

        resume_text = extract_text_from_txt(
            resume
        )

    extracted = extract_info_from_cv(
        resume_text
    )

    for key in st.session_state.application_info:

        if extracted.get(key):

            st.session_state.application_info[key] = (
                extracted[key]
            )

    st.sidebar.subheader(
        "🔍 Extracted Information"
    )

    for key, value in extracted.items():

        if value:

            st.sidebar.markdown(
                f"**{key.capitalize()}:** {value}"
            )

        else:

            st.sidebar.markdown(
                f"**{key.capitalize()}:** Not found"
            )

    status, data = check_application_goal()

    if status == "READY":

        st.session_state.goal_complete = True

        info = st.session_state.application_info

        st.session_state.application_summary = (
            f"JOB APPLICATION SUMMARY\n"
            f"=======================\n\n"
            f"Name: {info['name']}\n"
            f"Email: {info['email']}\n"
            f"Skills: {info['skills']}\n"
        )


# RESET BUTTON

if st.sidebar.button("🔄 Reset Application"):

    st.session_state.chat_history = []

    st.session_state.goal_complete = False

    st.session_state.application_summary = ""

    st.session_state.application_info = {
        "name": None,
        "email": None,
        "skills": None
    }

    st.rerun()


# CURRENT INFORMATION

with st.sidebar:

    st.divider()

    st.subheader("📋 Current Information")

    info = st.session_state.application_info

    st.write(
        f"**Name:** {info['name'] or '❌ Missing'}"
    )

    st.write(
        f"**Email:** {info['email'] or '❌ Missing'}"
    )

    st.write(
        f"**Skills:** {info['skills'] or '❌ Missing'}"
    )


# CHAT INPUT

user_input = st.chat_input(
    "Type your information here..."
)


if user_input:

    st.session_state.chat_history.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    extract_application_info(
        user_input
    )

    messages = []

    for message in st.session_state.chat_history:

        messages.append(
            (
                message["role"],
                message["content"]
            )
        )

    info = st.session_state.application_info

    context_message = f"""
Current application information:

Name: {info['name']}
Email: {info['email']}
Skills: {info['skills']}

Respond to the user's latest message and help
complete the application.
"""

    messages.append(
        (
            "system",
            context_message
        )
    )

    try:

        result = agent.invoke(
            {
                "messages": messages
            }
        )

        bot_reply = result["messages"][-1].content

    except Exception as e:

        bot_reply = (
            "❌ I couldn't connect to Ollama.\n\n"
            f"Please make sure Ollama is running and "
            f"the `{OLLAMA_MODEL}` model is installed.\n\n"
            f"Error: {str(e)}"
        )

    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "content": bot_reply
        }
    )

    status, data = check_application_goal()

    if status == "READY":

        st.session_state.goal_complete = True

        info = st.session_state.application_info

        st.session_state.application_summary = (
            f"JOB APPLICATION SUMMARY\n"
            f"=======================\n\n"
            f"Name: {info['name']}\n"
            f"Email: {info['email']}\n"
            f"Skills: {info['skills']}\n"
        )


# DISPLAY CHAT

for message in st.session_state.chat_history:

    if message["role"] == "user":

        with st.chat_message("user"):

            st.markdown(
                message["content"]
            )

    else:

        with st.chat_message("assistant"):

            st.markdown(
                message["content"]
            )


# GOAL COMPLETION

if st.session_state.goal_complete:

    st.success(
        "🎉 All information collected! "
        "You're ready to apply!"
    )

    st.subheader(
        "📋 Application Summary"
    )

    st.code(
        st.session_state.application_summary
    )

    st.download_button(
        label="📥 Download Application Summary",
        data=st.session_state.application_summary,
        file_name="application_summary.txt",
        mime="text/plain"
    )


# FOOTER

st.divider()

st.caption(
    f"🤖 Powered by Ollama ({OLLAMA_MODEL}) + "
    f"LangChain + Streamlit"
)