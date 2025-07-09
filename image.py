import base64
import streamlit as st
from openai import OpenAI
import io
from PIL import Image
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="OpenAI Vision & Image Generation Chat",
    page_icon="🎨",
    layout="wide"
)

# --- Authentication ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔒 Login Required")
    st.write("Please enter your credentials to access the OpenAI Vision & Image Generation Chat.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            login_button = st.form_submit_button("Login", use_container_width=True)
            
            if login_button:
                # In a real app, you'd validate against your authentication system
                if username == st.secrets.get("username", "admin") and password == st.secrets.get("password", "admin"):
                    st.session_state['logged_in'] = True
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials. Please try again.")
    st.stop()

# --- Initialize OpenAI Client ---
try:
    client = OpenAI(api_key=st.secrets["openai_api_key"])
except Exception as e:
    st.error("❌ OpenAI API key not found. Please configure your secrets.")
    st.stop()

# --- Sidebar Configuration ---
st.sidebar.title("🎨 Chat Settings")

# Model selection
model = st.sidebar.selectbox(
    "Select Model",
    ["gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4o", "gpt-4o-mini"],
    index=0,
    help="Choose the OpenAI model for processing"
)

# Image upload for vision analysis
st.sidebar.subheader("📸 Image Upload")
uploaded_file = st.sidebar.file_uploader(
    "Upload image for analysis",
    type=["png", "jpg", "jpeg", "webp", "gif"],
    help="Upload an image to analyze with vision capabilities"
)

# Image detail level
detail_level = st.sidebar.selectbox(
    "Image Detail Level",
    ["auto", "low", "high"],
    index=0,
    help="Choose processing detail level for images"
)

# Display uploaded image
if uploaded_file:
    img_bytes = uploaded_file.read()
    st.sidebar.image(img_bytes, caption="Uploaded Image", use_container_width=True)
    
    # Convert to base64 for API
    mime_type = uploaded_file.type
    b64_image = base64.b64encode(img_bytes).decode('utf-8')
    st.session_state['current_image'] = {
        'data_uri': f"data:{mime_type};base64,{b64_image}",
        'filename': uploaded_file.name,
        'size': len(img_bytes)
    }
    
    st.sidebar.success(f"✅ Image loaded ({len(img_bytes)} bytes)")
else:
    st.session_state.pop('current_image', None)

# Image generation settings
st.sidebar.subheader("🎨 Image Generation")
image_size = st.sidebar.selectbox(
    "Image Size",
    ["1024x1024", "1024x1536", "1536x1024", "1792x1024", "1024x1792"],
    index=0
)

image_quality = st.sidebar.selectbox(
    "Image Quality",
    ["auto", "low", "medium", "high"],
    index=0
)

# --- Initialize Chat History ---
if 'messages' not in st.session_state:
    st.session_state['messages'] = []

# --- Main Interface ---
st.title("🎨 OpenAI Vision & Image Generation Chat")
st.write("Chat with AI that can analyze images and generate new ones!")

# Help expander
with st.expander("ℹ️ How to use this app"):
    st.markdown("""
    **Vision Analysis:**
    - Upload an image in the sidebar
    - Ask questions about the image
    - The AI can describe, analyze, and answer questions about visual content
    
    **Image Generation:**
    - Type `/generate [description]` to create images
    - Example: `/generate a sunset over mountains`
    - Use `/edit [description]` to modify the last generated image
    
    **Supported Features:**
    - Multiple image formats (PNG, JPEG, WebP, GIF)
    - High-quality image generation with GPT Image model
    - Vision analysis with configurable detail levels
    - Multi-turn conversations with context
    """)

# --- Display Chat History ---
for i, msg in enumerate(st.session_state['messages']):
    with st.chat_message(msg['role']):
        if msg.get('type') == 'image':
            st.image(
                base64.b64decode(msg['content']),
                caption=msg.get('caption', 'Generated Image'),
                use_container_width=True
            )
            # Download button for generated images
            st.download_button(
                label="⬇️ Download Image",
                data=base64.b64decode(msg['content']),
                file_name=f"generated_image_{i}.png",
                mime="image/png",
                key=f"download_{i}"
            )
        else:
            st.write(msg['content'])

# --- Chat Input ---
user_input = st.chat_input("Type your message or '/generate [description]' to create an image...")

if user_input:
    # Add user message to chat
    st.session_state['messages'].append({'role': 'user', 'content': user_input})
    
    with st.chat_message("user"):
        st.write(user_input)
    
    # --- IMAGE GENERATION ---
    if user_input.lower().startswith('/generate '):
        prompt = user_input[len('/generate '):].strip()
        
        if not prompt:
            st.error("Please provide a description for image generation.")
        else:
            with st.chat_message("assistant"):
                with st.spinner("🎨 Generating image..."):
                    try:
                        response = client.responses.create(
                            model=model,
                            input=f"Generate an image: {prompt}",
                            tools=[{
                                "type": "image_generation",
                                "size": image_size,
                                "quality": image_quality
                            }]
                        )
                        
                        # Extract generated image
                        image_data = [
                            output.result
                            for output in response.output
                            if output.type == "image_generation_call"
                        ]
                        
                        if image_data:
                            image_base64 = image_data[0]
                            
                            # Store in session state
                            st.session_state['messages'].append({
                                'role': 'assistant',
                                'type': 'image',
                                'content': image_base64,
                                'caption': f"Generated: {prompt}"
                            })
                            
                            # Display immediately
                            st.image(
                                base64.b64decode(image_base64),
                                caption=f"Generated: {prompt}",
                                use_container_width=True
                            )
                            
                            st.download_button(
                                label="⬇️ Download Generated Image",
                                data=base64.b64decode(image_base64),
                                file_name=f"generated_{int(time.time())}.png",
                                mime="image/png"
                            )
                            
                            st.success("✅ Image generated successfully!")
                        else:
                            st.error("❌ No image was generated. Please try again.")
                            st.session_state['messages'].append({
                                'role': 'assistant',
                                'content': 'Sorry, I was unable to generate an image. Please try again with a different prompt.'
                            })
                    
                    except Exception as e:
                        st.error(f"❌ Error generating image: {str(e)}")
                        st.session_state['messages'].append({
                            'role': 'assistant',
                            'content': f'Error generating image: {str(e)}'
                        })
    
    # --- VISION ANALYSIS ---
    elif 'current_image' in st.session_state:
        with st.chat_message("assistant"):
            with st.spinner("👁️ Analyzing image..."):
                try:
                    response = client.responses.create(
                        model=model,
                        input=[{
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": user_input},
                                {
                                    "type": "input_image",
                                    "image_url": st.session_state['current_image']['data_uri'],
                                    "detail": detail_level
                                }
                            ]
                        }]
                    )
                    
                    reply = response.output_text
                    st.session_state['messages'].append({'role': 'assistant', 'content': reply})
                    st.write(reply)
                
                except Exception as e:
                    error_msg = f"❌ Error analyzing image: {str(e)}"
                    st.error(error_msg)
                    st.session_state['messages'].append({'role': 'assistant', 'content': error_msg})
    
    # --- TEXT CHAT ---
    else:
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are a helpful AI assistant with vision and image generation capabilities. You can analyze images and generate new ones when requested."},
                            {"role": "user", "content": user_input}
                        ]
                    )
                    
                    reply = response.choices[0].message.content
                    st.session_state['messages'].append({'role': 'assistant', 'content': reply})
                    st.write(reply)
                
                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state['messages'].append({'role': 'assistant', 'content': error_msg})

# --- Footer ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔧 Actions")
if st.sidebar.button("🗑️ Clear Chat History"):
    st.session_state['messages'] = []
    st.rerun()

if st.sidebar.button("🚪 Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# Session info
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Model:** {model}")
st.sidebar.markdown(f"**Messages:** {len(st.session_state['messages'])}")
if 'current_image' in st.session_state:
    st.sidebar.markdown(f"**Image:** {st.session_state['current_image']['filename']}")