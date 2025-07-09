import base64
import requests
import openai
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
            st.rerun()  # replaced experimental_rerun
        else:
            st.error("Invalid credentials, please try again.")
    st.stop()

# --- Authenticated ---
openai.api_key = st.secrets["api_key"]

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
    # Display uploaded file with the updated parameter
    st.sidebar.image(uploaded_file, caption="Uploaded image", use_container_width=True)
    img_bytes = uploaded_file.read()
    b64 = base64.b64encode(img_bytes).decode('utf-8')
    st.session_state['image_data_uri'] = f"data:image/png;base64,{b64}"
else:
    st.session_state.pop('image_data_uri', None)

# Initialize chat history
if 'messages' not in st.session_state:
    st.session_state['messages'] = []

# Display chat messages
for msg in st.session_state['messages']:
    with st.chat_message(msg['role']):
        st.write(msg['content'])

# Chat input
user_input = st.chat_input("Your message...")
if user_input:
    st.session_state['messages'].append({'role': 'user', 'content': user_input})

    # IMAGE GENERATION COMMAND
    if user_input.lower().startswith("/generate "):
        prompt = user_input[len("/generate "):].strip()
        img_resp = openai.Image.create(
            prompt=prompt,
            n=1,
            size="512x512"
        )
        img_url = img_resp['data'][0]['url']
        st.session_state['messages'].append({'role': 'assistant', 'content': f"![generated]({img_url})"})
        st.image(img_url, caption="Generated Image")
        img_data = requests.get(img_url).content
        st.download_button(
            label="Download Generated Image",
            data=img_data,
            file_name="generated.png",
            mime="image/png"
        )

    # VISION-CAPABLE AS WELL AS TEXT-ONLY CHAT
    else:
        system_msg = {"role": "system", "content": "You are a helpful assistant that can analyze images and chat."}
        if 'image_data_uri' in st.session_state:
            user_content = [
                {"type": "text",      "text": user_input},
                {"type": "image_url", "image_url": {"url": st.session_state['image_data_uri']}}
            ]
        else:
            user_content = user_input

        # Use the new Chat Completions API
        resp = openai.chat.completions.create(
            model=model,
            messages=[system_msg, {"role": "user", "content": user_content}]
        )
        assistant_msg = resp.choices[0].message.content
        st.session_state['messages'].append({'role': 'assistant', 'content': assistant_msg})
        st.chat_message("assistant").write(assistant_msg)
