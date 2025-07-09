import base64
import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="i-mage",
    page_icon="🤖",
    layout="wide"
)

# --- Authentication ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔒 Login Required")
    st.write("Please enter your credentials to access the Gemini 2.0 Chat.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            login_button = st.form_submit_button("Login", use_container_width=True)
            
            if login_button:
                if username == st.secrets.get("username", "admin") and password == st.secrets.get("password", "admin"):
                    st.session_state['logged_in'] = True
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials. Please try again.")
    st.stop()

# --- Initialize Google GenAI Client ---
try:
    client = genai.Client(api_key=st.secrets["google_api_key"])
except Exception as e:
    st.error("❌ Google API key not found. Please configure your secrets.")
    st.stop()

# --- Sidebar Configuration ---
st.sidebar.title("🤖 i-mage Settings")

# Model info
st.sidebar.info("**Model:** gemini-2.0-flash-preview-image-generation")
st.sidebar.markdown("💡 Gemini 2.0 excels at conversational image generation, editing, and vision analysis with world knowledge.")

# Image upload for vision analysis
st.sidebar.subheader("📸 Image Upload")
uploaded_file = st.sidebar.file_uploader(
    "Upload image for analysis/editing",
    type=["png", "jpg", "jpeg", "webp"],
    help="Upload an image for Gemini to analyze, edit, or use as context"
)

if uploaded_file:
    img_bytes = uploaded_file.read()
    st.sidebar.image(img_bytes, caption="Uploaded Image", use_container_width=True)
    
    # Store PIL image for Gemini
    st.session_state['current_image'] = Image.open(io.BytesIO(img_bytes))
    st.session_state['image_filename'] = uploaded_file.name
    st.sidebar.success(f"✅ Image loaded ({len(img_bytes)} bytes)")
else:
    st.session_state.pop('current_image', None)
    st.session_state.pop('image_filename', None)

# Generation tips
st.sidebar.subheader("💡 Generation Tips")
st.sidebar.markdown("""
**For best results:**
- Use clear, descriptive prompts
- Ask for images explicitly: "generate an image of..."
- For editing: "turn this into..." or "change the color to..."
- Supported languages: EN, ES, JA, ZH, HI
""")

# --- Initialize Chat History ---
if 'messages' not in st.session_state:
    st.session_state['messages'] = []

# --- Main Interface ---
st.title("🤖 i-mage")

# Help expander
with st.expander("ℹ️ How to use this app"):
    st.markdown("""
    **i-mage Features:**
    - **Conversational image generation**: Just describe what you want
    - **Image editing**: Upload an image and ask to modify it
    - **Vision analysis**: Ask questions about uploaded images
    - **Multi-turn editing**: Keep refining images through conversation
    - **Contextual understanding**: Leverages world knowledge for realistic results
    - **Interleaved outputs**: Mix of text explanations and generated images
    
    **Example Prompts:**
    - "Generate an image of a futuristic city with flying cars"
    - "Can you create a 3D rendered pig with wings flying over a sci-fi city?"
    - "What's in this image?" (with uploaded image)
    - "Turn this car into a convertible" (with uploaded car image)
    - "Now change the color to yellow" (follow-up editing)
    - "Generate an illustrated recipe for pasta"
    
    **Tips:**
    - Be explicit about wanting images: "generate", "create", "draw"
    - For editing, upload an image first, then describe changes
    - The model works best with English prompts
    - If only text is generated, try asking for images more explicitly
    """)

# --- Display Chat History ---
for i, msg in enumerate(st.session_state['messages']):
    with st.chat_message(msg['role']):
        if msg.get('type') == 'image':
            if isinstance(msg['content'], list):
                # Multiple images
                cols = st.columns(min(len(msg['content']), 2))
                for j, img_data in enumerate(msg['content']):
                    with cols[j % 2]:
                        st.image(img_data, caption=f"Generated Image {j+1}", use_container_width=True)
                        st.download_button(
                            label="⬇️ Download",
                            data=img_data,
                            file_name=f"gemini_generated_{i}_{j}.png",
                            mime="image/png",
                            key=f"download_{i}_{j}"
                        )
            else:
                # Single image
                st.image(msg['content'], caption=msg.get('caption', 'Generated Image'), use_container_width=True)
                st.download_button(
                    label="⬇️ Download Image",
                    data=msg['content'],
                    file_name=f"gemini_generated_{i}.png",
                    mime="image/png",
                    key=f"download_{i}"
                )
        else:
            st.write(msg['content'])

# --- Chat Input ---
user_input = st.chat_input("Describe what you want to generate, or ask about an uploaded image...")

if user_input:
    # Add user message to chat
    st.session_state['messages'].append({'role': 'user', 'content': user_input})
    
    with st.chat_message("user"):
        st.write(user_input)
    
    # --- GEMINI CONVERSATIONAL GENERATION ---
    with st.chat_message("assistant"):
        with st.spinner("🤖 Processing with Gemini 2.0..."):
            try:
                # Prepare content for Gemini
                if 'current_image' in st.session_state:
                    # Include uploaded image for editing/analysis
                    contents = [user_input, st.session_state['current_image']]
                    st.info(f"📸 Using uploaded image: {st.session_state.get('image_filename', 'Unknown')}")
                else:
                    # Text-only input
                    contents = user_input
                
                response = client.models.generate_content(
                    model="gemini-2.0-flash-preview-image-generation",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_modalities=['TEXT', 'IMAGE']
                    )
                )
                
                # Process response parts
                text_response = ""
                generated_images = []
                
                for part in response.candidates[0].content.parts:
                    if part.text is not None:
                        text_response += part.text
                    elif part.inline_data is not None:
                        # Convert inline data to bytes
                        img_buffer = io.BytesIO()
                        image = Image.open(io.BytesIO(part.inline_data.data))
                        image.save(img_buffer, format='PNG')
                        img_bytes = img_buffer.getvalue()
                        generated_images.append(img_bytes)
                
                # Display text response first
                if text_response:
                    st.write(text_response)
                    st.session_state['messages'].append({
                        'role': 'assistant',
                        'content': text_response
                    })
                
                # Display generated images
                if generated_images:
                    if len(generated_images) == 1:
                        st.image(generated_images[0], caption="Generated with Gemini 2.0", use_container_width=True)
                        st.download_button(
                            label="⬇️ Download Generated Image",
                            data=generated_images[0],
                            file_name=f"gemini_generated_{int(time.time())}.png",
                            mime="image/png",
                            key="download_current"
                        )
                        
                        st.session_state['messages'].append({
                            'role': 'assistant',
                            'type': 'image',
                            'content': generated_images[0],
                            'caption': 'Generated with Gemini 2.0'
                        })
                    else:
                        # Multiple images
                        cols = st.columns(min(len(generated_images), 2))
                        for i, img_data in enumerate(generated_images):
                            with cols[i % 2]:
                                st.image(img_data, caption=f"Generated Image {i+1}", use_container_width=True)
                                st.download_button(
                                    label=f"⬇️ Download {i+1}",
                                    data=img_data,
                                    file_name=f"gemini_generated_{int(time.time())}_{i}.png",
                                    mime="image/png",
                                    key=f"download_current_{i}"
                                )
                        
                        st.session_state['messages'].append({
                            'role': 'assistant',
                            'type': 'image',
                            'content': generated_images,
                            'caption': 'Generated with Gemini 2.0'
                        })
                    
                    st.success(f"✅ Generated {len(generated_images)} image(s) successfully!")
                
                # Handle cases where no content was generated
                if not text_response and not generated_images:
                    warning_msg = "⚠️ No content was generated. Try being more explicit about wanting images or text."
                    st.warning(warning_msg)
                    st.session_state['messages'].append({
                        'role': 'assistant',
                        'content': 'I didn\'t generate any content. Try asking for images explicitly, like "generate an image of..." or "create a picture showing..." You can also ask me to explain or describe things if you want text responses.'
                    })
                elif not generated_images and "generate" in user_input.lower():
                    st.info("💡 The model provided a text response. If you wanted an image, try asking more explicitly for visual content.")
            
            except Exception as e:
                error_msg = f"❌ Error with Gemini 2.0: {str(e)}"
                st.error(error_msg)
                st.session_state['messages'].append({
                    'role': 'assistant',
                    'content': f'Sorry, I encountered an error: {str(e)}. Please try again with a different prompt.'
                })

# --- Footer ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔧 Actions")
if st.sidebar.button("🗑️ Clear Chat History"):
    st.session_state['messages'] = []
    st.rerun()

if st.sidebar.button("📸 Clear Uploaded Image"):
    st.session_state.pop('current_image', None)
    st.session_state.pop('image_filename', None)
    st.rerun()

if st.sidebar.button("🚪 Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# Session info
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Session Info")
st.sidebar.markdown(f"**Messages:** {len(st.session_state['messages'])}")
if 'current_image' in st.session_state:
    st.sidebar.markdown(f"**Image:** {st.session_state.get('image_filename', 'Uploaded')} ✅")
else:
    st.sidebar.markdown("**Image:** None")