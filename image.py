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

st.title("🤖 OpenAI Image Chat")
st.write("Chat with AI and generate images! Use `/generate [prompt]` to create images.")

st.sidebar.title("⚙️ Settings")

# Model selection for chat
chat_model = st.sidebar.selectbox(
    "Choose Chat Model",
    ["gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"],
    help="Model for text chat and vision analysis"
)

# Image generation model
image_model = st.sidebar.selectbox(
    "Choose Image Model",
    ["dall-e-3", "dall-e-2"],
    help="Model for image generation"
)

# Image upload for chat
uploaded_file = st.file_uploader(
    "📷 Upload an image to include in your message", 
    type=["png", "jpg", "jpeg", "webp"],
    help="Upload an image to send with your next message"
)

if uploaded_file:
    img_bytes = uploaded_file.read()
    st.image(img_bytes, caption="Image ready to send", width=300)
    mime = uploaded_file.type
    b64 = base64.b64encode(img_bytes).decode('utf-8')
    st.session_state['pending_image'] = {
        'data': f"data:{mime};base64,{b64}",
        'bytes': img_bytes,
        'name': uploaded_file.name
    }
else:
    st.session_state.pop('pending_image', None)

# Clear chat button
if st.sidebar.button("🗑️ Clear Chat"):
    st.session_state['messages'] = []
    st.rerun()

# Initialize messages
if 'messages' not in st.session_state:
    st.session_state['messages'] = []

# --- Display chat history ---
for i, msg in enumerate(st.session_state['messages']):
    with st.chat_message(msg['role']):
        if msg.get("type") == "image":
            try:
                decoded_image = base64.b64decode(msg["content"])
                st.image(decoded_image, caption=msg.get("caption", "Generated Image"), use_container_width=True)
                
                # Add download button for each image
                st.download_button(
                    label="Download Image",
                    data=decoded_image,
                    file_name=f"generated_image_{i}.png",
                    mime="image/png",
                    key=f"download_{i}"
                )
            except Exception as e:
                st.error(f"Error displaying image: {e}")
        elif msg.get("type") == "user_image":
            # Display user uploaded image
            try:
                decoded_image = base64.b64decode(msg["image_data"])
                st.image(decoded_image, caption=msg.get("image_name", "Uploaded Image"), width=300)
                if msg.get("content"):
                    st.write(msg["content"])
            except Exception as e:
                st.error(f"Error displaying user image: {e}")
        else:
            st.write(msg["content"])

# --- Chat input ---
user_input = st.chat_input("Type your message or use '/generate [prompt]' to create images...")

if user_input:
    # Check if user has uploaded an image
    has_image = 'pending_image' in st.session_state
    
    # Display user message with image if present
    with st.chat_message("user"):
        if has_image:
            st.image(st.session_state['pending_image']['bytes'], 
                    caption=st.session_state['pending_image']['name'], 
                    width=300)
        if user_input.strip():  # Only show text if there's actual content
            st.write(user_input)
    
    # Add user message to history
    if has_image:
        # Store image data in base64 for history
        image_b64 = base64.b64encode(st.session_state['pending_image']['bytes']).decode('utf-8')
        st.session_state['messages'].append({
            'role': 'user',
            'type': 'user_image',
            'content': user_input if user_input.strip() else "",
            'image_data': image_b64,
            'image_name': st.session_state['pending_image']['name']
        })
    else:
        st.session_state['messages'].append({'role': 'user', 'content': user_input})

    # ---- IMAGE GENERATION COMMAND ----
    if user_input.lower().startswith("/generate "):
        prompt = user_input[len("/generate "):].strip()
        
        if not prompt:
            with st.chat_message("assistant"):
                st.error("Please provide a prompt after /generate. Example: `/generate a cat sitting on a table`")
            st.session_state['messages'].append({
                'role': 'assistant',
                'content': 'Please provide a prompt after /generate. Example: `/generate a cat sitting on a table`'
            })
        else:
            with st.spinner(f"Generating image with {image_model}..."):
                try:
                    # Generate image using Images API
                    response = client.images.generate(
                        model=image_model,
                        prompt=prompt,
                        size="1024x1024" if image_model == "dall-e-3" else "512x512",
                        quality="standard" if image_model == "dall-e-3" else None,
                        n=1,
                        response_format="b64_json"
                    )
                    
                    # Get the base64 image
                    image_base64 = response.data[0].b64_json
                    
                    # Validate base64 data
                    try:
                        decoded_image = base64.b64decode(image_base64)
                        
                        # Add to message history
                        st.session_state['messages'].append({
                            'role': 'assistant',
                            'type': 'image',
                            'content': image_base64,
                            'caption': f"Generated with {image_model}: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
                        })
                        
                        # Display the generated image
                        with st.chat_message("assistant"):
                            st.success(f"✅ Image generated successfully with {image_model}!")
                            st.image(
                                decoded_image, 
                                caption=f"Prompt: {prompt}", 
                                use_container_width=True
                            )
                            
                            # Download button
                            st.download_button(
                                label="💾 Download Generated Image",
                                data=decoded_image,
                                file_name=f"generated_{len(st.session_state['messages'])}.png",
                                mime="image/png",
                                type="primary"
                            )
                            
                            # Show revised prompt if available (DALL-E 3)
                            if hasattr(response.data[0], 'revised_prompt') and response.data[0].revised_prompt:
                                with st.expander("🎨 See Revised Prompt"):
                                    st.write(response.data[0].revised_prompt)
                                    
                    except Exception as decode_error:
                        error_msg = f"❌ Error decoding generated image: {decode_error}"
                        with st.chat_message("assistant"):
                            st.error(error_msg)
                        st.session_state['messages'].append({
                            'role': 'assistant',
                            'content': error_msg
                        })
                        
                except Exception as e:
                    error_msg = f"❌ Error generating image: {str(e)}"
                    with st.chat_message("assistant"):
                        st.error(error_msg)
                        if "billing" in str(e).lower():
                            st.info("💡 This might be a billing issue. Check your OpenAI account credits.")
                        elif "rate" in str(e).lower():
                            st.info("💡 You might be hitting rate limits. Try again in a moment.")
                    
                    st.session_state['messages'].append({
                        'role': 'assistant',
                        'content': error_msg
                    })

    # ---- VISION ANALYSIS OR REGULAR CHAT ----
    else:
        try:
            # Check if user uploaded an image with this message
            if has_image:
                # Clear the pending image after using it
                image_data_uri = st.session_state['pending_image']['data']
                st.session_state.pop('pending_image', None)
                
                with st.spinner("Analyzing image..."):
                    # Use vision capabilities for image analysis
                    response = client.chat.completions.create(
                        model=chat_model,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": user_input if user_input.strip() else "What do you see in this image?"},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": image_data_uri
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=1000
                    )
                reply = response.choices[0].message.content
                
                with st.chat_message("assistant"):
                    st.write("🔍 **Image Analysis:**")
                    st.write(reply)
                    
            else:
                # Regular text chat - include recent message history for context
                chat_messages = [
                    {
                        "role": "system", 
                        "content": "You are a helpful AI assistant. You can chat about any topic and help users with various tasks. When users want to generate images, they should use the /generate command."
                    }
                ]
                
                # Add recent messages for context (last 10 text messages)
                recent_messages = []
                for msg in st.session_state['messages'][-20:]:  # Look at last 20 messages
                    if msg.get("type") == "user_image":
                        # For user images, include the text part only
                        if msg.get("content"):
                            recent_messages.append({"role": "user", "content": f"[Image uploaded] {msg['content']}"})
                        else:
                            recent_messages.append({"role": "user", "content": "[Image uploaded without text]"})
                    elif msg.get("type") != "image":  # Exclude generated images
                        recent_messages.append({"role": msg["role"], "content": msg["content"]})
                
                # Take only the last 10 for context
                chat_messages.extend(recent_messages[-10:])
                
                with st.spinner("Thinking..."):
                    response = client.chat.completions.create(
                        model=chat_model,
                        messages=chat_messages,
                        max_tokens=1000
                    )
                reply = response.choices[0].message.content
                
                with st.chat_message("assistant"):
                    st.write(reply)

            # Add assistant reply to history
            st.session_state['messages'].append({'role': 'assistant', 'content': reply})
                
        except Exception as e:
            error_msg = f"❌ Error in chat: {str(e)}"
            with st.chat_message("assistant"):
                st.error(error_msg)
            st.session_state['messages'].append({
                'role': 'assistant',
                'content': error_msg
            })

# --- Sidebar Info ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 📖 How to Use")
st.sidebar.markdown("""
**Image Analysis:**
- Upload an image above the chat input
- Send it with or without text
- AI will analyze the image and respond

**Image Generation:**
- Use `/generate [your prompt]`
- Example: `/generate a sunset over mountains`

**Text Chat:**
- Just type your message normally
- Context is maintained across messages

**Tips:**
- Images are analyzed immediately when sent
- Be specific in your image prompts
- Try different models for different results
- DALL-E 3 generally produces better quality images
""")

# Show current settings
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔧 Current Settings")
st.sidebar.markdown(f"**Chat Model:** {chat_model}")
st.sidebar.markdown(f"**Image Model:** {image_model}")
st.sidebar.markdown(f"**Messages:** {len(st.session_state.get('messages', []))}")
pending_image = st.session_state.get('pending_image')
if pending_image:
    st.sidebar.markdown("**Pending Image:** ✅ Ready to send")
else:
    st.sidebar.markdown("**Pending Image:** ❌ None")

# Debug info (toggle)
if st.sidebar.checkbox("🐛 Show Debug Info"):
    st.sidebar.markdown("### Debug Information")
    st.sidebar.json({
        "chat_model": chat_model,
        "image_model": image_model,
        "messages_count": len(st.session_state.get('messages', [])),
        "has_pending_image": 'pending_image' in st.session_state,
        "logged_in": st.session_state.get('logged_in', False)
    })