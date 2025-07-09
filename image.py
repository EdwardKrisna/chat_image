import base64
from openai import OpenAI
import streamlit as st

# --- Page config ---
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

# --- Authenticated session ---
client = OpenAI(api_key=st.secrets["api_key"])

st.sidebar.title("Settings")

# Only include models that support image generation
IMAGE_GENERATION_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano"]

model = st.sidebar.selectbox(
    "Choose model",
    IMAGE_GENERATION_MODELS,
    help="These models support image generation"
)

uploaded_file = st.sidebar.file_uploader(
    "Upload an image (for vision analysis)", type=["png", "jpg", "jpeg"]
)

if uploaded_file:
    img_bytes = uploaded_file.read()
    st.sidebar.image(img_bytes, caption="Uploaded image", use_container_width=True)
    mime = uploaded_file.type
    b64 = base64.b64encode(img_bytes).decode('utf-8')
    st.session_state['image_data_uri'] = f"data:{mime};base64,{b64}"
else:
    st.session_state.pop('image_data_uri', None)

if 'messages' not in st.session_state:
    st.session_state['messages'] = []

# --- Display chat history, with image support for assistant ---
for msg in st.session_state['messages']:
    with st.chat_message(msg['role']):
        if msg.get("type") == "image":
            try:
                st.image(base64.b64decode(msg["content"]), caption=msg.get("caption", ""), use_container_width=True)
            except Exception as e:
                st.error(f"Error displaying image: {e}")
        else:
            st.write(msg["content"])

# --- Chat input ---
user_input = st.chat_input("Your message... (Use '/generate [prompt]' to create images)")

if user_input:
    # Display user message
    with st.chat_message("user"):
        st.write(user_input)
    st.session_state['messages'].append({'role': 'user', 'content': user_input})

    if user_input.lower().startswith("/generate "):
        prompt = user_input[len("/generate "):].strip()
        
        if not prompt:
            st.error("Please provide a prompt after /generate")
            st.stop()
            
        with st.spinner("Generating image with DALL-E 3..."):
            try:
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1,
                    response_format="b64_json"
                )
                
                image_base64 = response.data[0].b64_json
                decoded_image = base64.b64decode(image_base64)
                
                st.session_state['messages'].append({
                    'role': 'assistant',
                    'type': 'image',
                    'content': image_base64,
                    'caption': f"Generated: {prompt[:50]}..."
                })
                
                with st.chat_message("assistant"):
                    st.success("Image generated successfully with DALL-E 3!")
                    st.image(decoded_image, caption=f"Generated: {prompt[:50]}...", use_container_width=True)
                    st.download_button(
                        label="Download Generated Image",
                        data=decoded_image,
                        file_name="generated.png",
                        mime="image/png"
                    )
                    
            except Exception as e:
                error_msg = f"Error generating image: {str(e)}"
                st.error(error_msg)
                st.session_state['messages'].append({
                    'role': 'assistant',
                    'content': error_msg
                })

    # ---- VISION/ANALYSIS OR TEXT CHAT ----
    else:
        try:
            # If user uploaded an image, send it for analysis
            if 'image_data_uri' in st.session_state:
                vision_input = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": user_input},
                            {
                                "type": "input_image",
                                "image_url": st.session_state['image_data_uri']
                            }
                        ]
                    }
                ]
                with st.spinner("Analyzing image..."):
                    response = client.responses.create(
                        model=model,
                        input=vision_input,
                    )
                # The vision output is always text (output_text)
                reply = response.output_text
            else:
                # Text-only chat
                with st.spinner("Thinking..."):
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that can analyze images and chat."},
                            {"role": "user", "content": user_input}
                        ]
                    )
                reply = response.choices[0].message.content

            st.session_state['messages'].append({'role': 'assistant', 'content': reply})
            with st.chat_message("assistant"):
                st.write(reply)
                
        except Exception as e:
            error_msg = f"Error in chat: {str(e)}"
            st.error(error_msg)
            st.session_state['messages'].append({
                'role': 'assistant',
                'content': error_msg
            })

# --- Debug info in sidebar ---
if st.sidebar.checkbox("Show Debug Info"):
    st.sidebar.write("Current model:", model)
    st.sidebar.write("Messages count:", len(st.session_state.get('messages', [])))
    if 'image_data_uri' in st.session_state:
        st.sidebar.write("Image uploaded: Yes")
    else:
        st.sidebar.write("Image uploaded: No")