import base64
import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="Gemini & Imagen Vision Chat",
    page_icon="🤖",
    layout="wide"
)

# --- Authentication ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔒 Login Required")
    st.write("Please enter your credentials to access the Gemini & Imagen Chat.")
    
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
st.sidebar.title("🤖 Chat Settings")

# Model selection
model_type = st.sidebar.selectbox(
    "Select Model Type",
    ["Gemini (Vision & Generation)", "Imagen (Specialized Generation)"],
    index=0,
    help="Choose between Gemini for conversational image generation or Imagen for specialized image generation"
)

if model_type == "Gemini (Vision & Generation)":
    model = "gemini-2.0-flash-preview-image-generation"
    st.sidebar.info("💡 Gemini excels at contextual image generation and editing with conversational abilities.")
else:
    imagen_model = st.sidebar.selectbox(
        "Select Imagen Model",
        ["imagen-4.0-generate-preview-06-06", "imagen-3.0-generate-preview", "imagen-4.0-ultra-generate-preview"],
        index=0,
        help="Choose the Imagen model version"
    )
    model = imagen_model
    st.sidebar.info("💡 Imagen excels at photorealistic images, artistic styles, and specialized editing.")

# Image upload for vision analysis (Gemini only)
if model_type == "Gemini (Vision & Generation)":
    st.sidebar.subheader("📸 Image Upload")
    uploaded_file = st.sidebar.file_uploader(
        "Upload image for analysis/editing",
        type=["png", "jpg", "jpeg", "webp"],
        help="Upload an image for Gemini to analyze or edit"
    )
    
    if uploaded_file:
        img_bytes = uploaded_file.read()
        st.sidebar.image(img_bytes, caption="Uploaded Image", use_container_width=True)
        
        # Store PIL image for Gemini
        st.session_state['current_image'] = Image.open(io.BytesIO(img_bytes))
        st.sidebar.success(f"✅ Image loaded ({len(img_bytes)} bytes)")
    else:
        st.session_state.pop('current_image', None)

# Image generation settings
st.sidebar.subheader("🎨 Generation Settings")

if model_type == "Imagen (Specialized Generation)":
    num_images = st.sidebar.slider(
        "Number of Images",
        min_value=1,
        max_value=4 if "ultra" not in model else 1,
        value=1 if "ultra" in model else 2,
        help="Number of images to generate (Imagen 4 Ultra: max 1)"
    )
    
    aspect_ratio = st.sidebar.selectbox(
        "Aspect Ratio",
        ["1:1", "3:4", "4:3", "9:16", "16:9"],
        index=0,
        help="Choose the aspect ratio for generated images"
    )
    
    person_generation = st.sidebar.selectbox(
        "Person Generation",
        ["allow_adult", "dont_allow", "allow_all"],
        index=0,
        help="Control whether to generate images with people"
    )
else:
    st.sidebar.info("Gemini uses conversational settings - just describe what you want!")

# --- Initialize Chat History ---
if 'messages' not in st.session_state:
    st.session_state['messages'] = []

# --- Main Interface ---
st.title("🤖 Gemini & Imagen Vision Chat")
st.write(f"Chat with AI using **{model_type}** for vision analysis and image generation!")

# Help expander
with st.expander("ℹ️ How to use this app"):
    st.markdown("""
    **Gemini Model Features:**
    - Conversational image generation and editing
    - Upload images for analysis and modification
    - Multi-turn editing: "Turn this car into a convertible", "Now change the color to yellow"
    - Contextual understanding with world knowledge
    - Interleaved text and image outputs
    
    **Imagen Model Features:**
    - Specialized high-quality image generation
    - Photorealistic and artistic styles
    - Multiple images per request (except Ultra)
    - Configurable aspect ratios and generation settings
    - Best for product design, logos, and detailed artwork
    
    **Commands:**
    - `/generate [description]` - Generate images
    - `/edit [description]` - Edit uploaded images (Gemini only)
    - Regular chat works too - just describe what you want!
    """)

# --- Display Chat History ---
for i, msg in enumerate(st.session_state['messages']):
    with st.chat_message(msg['role']):
        if msg.get('type') == 'image':
            if isinstance(msg['content'], list):
                # Multiple images
                cols = st.columns(min(len(msg['content']), 3))
                for j, img_data in enumerate(msg['content']):
                    with cols[j % 3]:
                        st.image(img_data, caption=f"Generated Image {j+1}", use_container_width=True)
                        st.download_button(
                            label="⬇️ Download",
                            data=img_data,
                            file_name=f"generated_image_{i}_{j}.png",
                            mime="image/png",
                            key=f"download_{i}_{j}"
                        )
            else:
                # Single image
                st.image(msg['content'], caption=msg.get('caption', 'Generated Image'), use_container_width=True)
                st.download_button(
                    label="⬇️ Download Image",
                    data=msg['content'],
                    file_name=f"generated_image_{i}.png",
                    mime="image/png",
                    key=f"download_{i}"
                )
        else:
            st.write(msg['content'])

# --- Chat Input ---
user_input = st.chat_input("Type your message or describe what you want to generate...")

if user_input:
    # Add user message to chat
    st.session_state['messages'].append({'role': 'user', 'content': user_input})
    
    with st.chat_message("user"):
        st.write(user_input)
    
    # --- IMAGEN IMAGE GENERATION ---
    if model_type == "Imagen (Specialized Generation)":
        with st.chat_message("assistant"):
            with st.spinner("🎨 Generating images with Imagen..."):
                try:
                    response = client.models.generate_images(
                        model=model,
                        prompt=user_input,
                        config=types.GenerateImagesConfig(
                            number_of_images=num_images,
                            aspect_ratio=aspect_ratio,
                            person_generation=person_generation
                        )
                    )
                    
                    generated_images = []
                    for generated_image in response.generated_images:
                        # Convert PIL image to bytes
                        img_buffer = io.BytesIO()
                        generated_image.image.save(img_buffer, format='PNG')
                        img_bytes = img_buffer.getvalue()
                        generated_images.append(img_bytes)
                    
                    if generated_images:
                        # Store images in session state
                        if len(generated_images) == 1:
                            st.session_state['messages'].append({
                                'role': 'assistant',
                                'type': 'image',
                                'content': generated_images[0],
                                'caption': f"Generated with {model}"
                            })
                            # Display single image
                            st.image(generated_images[0], caption=f"Generated with {model}", use_container_width=True)
                            st.download_button(
                                label="⬇️ Download Generated Image",
                                data=generated_images[0],
                                file_name=f"imagen_generated_{int(time.time())}.png",
                                mime="image/png"
                            )
                        else:
                            st.session_state['messages'].append({
                                'role': 'assistant',
                                'type': 'image',
                                'content': generated_images,
                                'caption': f"Generated with {model}"
                            })
                            # Display multiple images
                            cols = st.columns(min(len(generated_images), 3))
                            for j, img_data in enumerate(generated_images):
                                with cols[j % 3]:
                                    st.image(img_data, caption=f"Image {j+1}", use_container_width=True)
                                    st.download_button(
                                        label="⬇️ Download",
                                        data=img_data,
                                        file_name=f"imagen_generated_{int(time.time())}_{j}.png",
                                        mime="image/png",
                                        key=f"download_current_{j}"
                                    )
                        
                        st.success(f"✅ Generated {len(generated_images)} image(s) successfully!")
                    else:
                        st.error("❌ No images were generated.")
                        st.session_state['messages'].append({
                            'role': 'assistant',
                            'content': 'Sorry, I was unable to generate images. Please try again with a different prompt.'
                        })
                
                except Exception as e:
                    st.error(f"❌ Error generating images: {str(e)}")
                    st.session_state['messages'].append({
                        'role': 'assistant',
                        'content': f'Error generating images: {str(e)}'
                    })
    
    # --- GEMINI CONVERSATIONAL GENERATION ---
    else:
        with st.chat_message("assistant"):
            with st.spinner("🤖 Processing with Gemini..."):
                try:
                    # Prepare content for Gemini
                    if 'current_image' in st.session_state:
                        # Include uploaded image for editing/analysis
                        contents = [user_input, st.session_state['current_image']]
                    else:
                        # Text-only input
                        contents = user_input
                    
                    response = client.models.generate_content(
                        model=model,
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
                    
                    # Display text response
                    if text_response:
                        st.write(text_response)
                        st.session_state['messages'].append({
                            'role': 'assistant',
                            'content': text_response
                        })
                    
                    # Display generated images
                    if generated_images:
                        for i, img_data in enumerate(generated_images):
                            st.image(img_data, caption=f"Generated Image {i+1}", use_container_width=True)
                            st.download_button(
                                label=f"⬇️ Download Image {i+1}",
                                data=img_data,
                                file_name=f"gemini_generated_{int(time.time())}_{i}.png",
                                mime="image/png",
                                key=f"download_gemini_{i}"
                            )
                        
                        st.session_state['messages'].append({
                            'role': 'assistant',
                            'type': 'image',
                            'content': generated_images if len(generated_images) > 1 else generated_images[0],
                            'caption': 'Generated with Gemini'
                        })
                    
                    if not text_response and not generated_images:
                        st.warning("⚠️ No text or images were generated. Try being more explicit about wanting images.")
                        st.session_state['messages'].append({
                            'role': 'assistant',
                            'content': 'I didn\'t generate any content. Try asking for images explicitly, like "generate an image of..." or "create a picture showing..."'
                        })
                
                except Exception as e:
                    st.error(f"❌ Error with Gemini: {str(e)}")
                    st.session_state['messages'].append({
                        'role': 'assistant',
                        'content': f'Error: {str(e)}'
                    })

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
if model_type == "Gemini (Vision & Generation)" and 'current_image' in st.session_state:
    st.sidebar.markdown("**Image:** Uploaded ✅")

# Model comparison info
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Model Comparison")
st.sidebar.markdown("""
**Gemini:**
- Conversational AI
- Context understanding
- Multi-turn editing
- World knowledge

**Imagen:**
- Photorealistic quality
- Artistic styles
- Multiple images
- Specialized editing
""")