import base64
import requests
from openai import OpenAI
import streamlit as st

# Page config
st.set_page_config(page_title="OpenAI Image Chat", page_icon="🤖", layout="wide")

# --- Login ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔒 Login")
    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if user == st.secrets["user"] and pwd == st.secrets["password"]:
            st.session_state['logged_in'] = True
            st.rerun()
        else:
            st.error("Invalid credentials, please try again.")
    st.stop()

# --- Authenticated ---
client = OpenAI(api_key=st.secrets["api_key"])

st.sidebar.title("Settings")
model = st.sidebar.selectbox(
    "Choose model", 
    ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano"]
)

# Upload an image for vision analysis
uploaded_file = st.sidebar.file_uploader(
    "Upload an image", type=["png", "jpg", "jpeg"]
)

if uploaded_file:
    img_bytes = uploaded_file.read()
    st.sidebar.image(img_bytes, caption="Uploaded image", use_container_width=True)
    b64 = base64.b64encode(img_bytes).decode('utf-8')
    st.session_state['image_data_uri'] = f"data:image/png;base64,{b64}"
else:
    st.session_state.pop('image_data_uri', None)

# Initialize chat history
if 'messages' not in st.session_state:
    st.session_state['messages'] = []

# Display chat messages (with image support for assistant)
for msg in st.session_state['messages']:
    with st.chat_message(msg['role']):
        if msg.get("type") == "image":
            st.image(msg["content"], caption=msg.get("caption", ""), use_container_width=True)
        else:
            st.write(msg["content"])

# Chat input
user_input = st.chat_input("Your message...")
if user_input:
    st.session_state['messages'].append({'role': 'user', 'content': user_input})

    # IMAGE GENERATION COMMAND using RESPONSES API
    if user_input.lower().startswith("/generate "):
        prompt = user_input[len("/generate "):].strip()
        response = client.responses.create(
            model=model,
            input=prompt,
            tools=[{"type": "image_generation"}]
        )
        # Get base64 image output
        image_data = [
            output.result
            for output in response.output
            if output.type == "image_generation_call"
        ]
        if image_data:
            image_base64 = image_data[0]
            # Display in chat
            st.session_state['messages'].append({
                'role': 'assistant',
                'type': 'image',
                'content': f"data:image/png;base64,{image_base64}",
                'caption': "Generated Image"
            })
            with st.chat_message("assistant"):
                st.image(base64.b64decode(image_base64), caption="Generated Image", use_container_width=True)
                st.download_button(
                    label="Download Generated Image",
                    data=base64.b64decode(image_base64),
                    file_name="generated.png",
                    mime="image/png"
                )
        else:
            st.session_state['messages'].append({
                'role': 'assistant',
                'content': 'No image was generated.'
            })
            st.chat_message("assistant").write("No image was generated.")

    # VISION-CAPABLE OR TEXT-ONLY CHAT (old code)
    else:
        system_msg = {"role": "system", "content": "You are a helpful assistant that can analyze images and chat."}
        if 'image_data_uri' in st.session_state:
            user_content = [
                {"type": "text",      "text": user_input},
                {"type": "image_url", "image_url": {"url": st.session_state['image_data_uri']}}
            ]
        else:
            user_content = user_input

        # Use Chat Completions API for text/vision
        resp = client.chat.completions.create(
            model=model,
            messages=[system_msg, {"role": "user", "content": user_content}]
        )
        assistant_msg = resp.choices[0].message.content
        st.session_state['messages'].append({'role': 'assistant', 'content': assistant_msg})
        with st.chat_message("assistant"):
            st.write(assistant_msg)
