import base64
from openai import OpenAI
import streamlit as st

# --- Page config ---
st.set_page_config(page_title="i-mage", page_icon="🤖", layout="wide")

# --- Login ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔒 i-mage Login")
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

st.title("🤖 i-mage")
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
            # Check for different types of image generation requests
            is_recreation = any(word in prompt.lower() for word in ["recreate", "upload", "this image"])
            is_editing = any(word in prompt.lower() for word in ["edit", "remove", "add", "change", "modify", "without", "dont include", "don't include"])
            
            if (is_recreation or is_editing) and has_image:
                # Handle image recreation or editing
                image_data_uri = st.session_state['pending_image']['data']
                
                with st.spinner("Analyzing uploaded image..."):
                    try:
                        if is_editing:
                            # For editing, create a more specific analysis prompt
                            analysis_prompt = f"Describe this image in detail for art generation purposes. Include all elements, colors, composition, style, subjects, lighting, and mood. Be very specific about objects, people, and background elements. This description will be used to recreate the image with modifications: {prompt}"
                        else:
                            # For recreation, use general analysis
                            analysis_prompt = "Describe this image in detail for art generation purposes. Include colors, composition, style, subjects, lighting, and mood. Be very descriptive and artistic."
                        
                        # First, analyze the uploaded image
                        describe_response = client.chat.completions.create(
                            model=chat_model,
                            messages=[
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": analysis_prompt},
                                        {
                                            "type": "image_url",
                                            "image_url": {
                                                "url": image_data_uri
                                            }
                                        }
                                    ]
                                }
                            ],
                            max_tokens=500
                        )
                        
                        description = describe_response.choices[0].message.content
                        
                        # Process the editing request
                        if is_editing:
                            # Create a more sophisticated editing prompt
                            editing_instruction = prompt.replace("edit the image", "").replace("edit", "").strip()
                            
                            # Use AI to create a better generation prompt
                            edit_prompt_response = client.chat.completions.create(
                                model=chat_model,
                                messages=[
                                    {
                                        "role": "system",
                                        "content": "You are an expert at creating image generation prompts. Given an image description and editing instructions, create a new detailed prompt that incorporates the changes."
                                    },
                                    {
                                        "role": "user",
                                        "content": f"Original image description: {description}\n\nEditing instruction: {editing_instruction}\n\nCreate a new detailed prompt for image generation that keeps the original elements but applies the requested changes. Be specific and artistic."
                                    }
                                ],
                                max_tokens=300
                            )
                            
                            generation_prompt = edit_prompt_response.choices[0].message.content
                            
                            # Show the editing process to user
                            with st.chat_message("assistant"):
                                st.info("🎨 **Editing Process:**")
                                st.write(f"**Original Description:** {description[:200]}...")
                                st.write(f"**Edit Request:** {editing_instruction}")
                                st.write(f"**New Generation Prompt:** {generation_prompt[:200]}...")
                                st.write("**Now generating edited image...**")
                        else:
                            # For recreation
                            generation_prompt = f"Create an artistic recreation of: {description}"
                            
                            # Show the description to user
                            with st.chat_message("assistant"):
                                st.info("🔍 **Analyzing your image...**")
                                st.write(f"**Description:** {description}")
                                st.write("**Now generating a similar image...**")
                        
                    except Exception as e:
                        error_msg = f"❌ Error analyzing image: {str(e)}"
                        with st.chat_message("assistant"):
                            st.error(error_msg)
                        st.session_state['messages'].append({
                            'role': 'assistant',
                            'content': error_msg
                        })
                        st.stop()
                        
            elif (is_recreation or is_editing) and not has_image:
                # No image uploaded but user wants to recreate/edit
                with st.chat_message("assistant"):
                    st.warning("🖼️ **No Image to Edit/Recreate**")
                    st.write("To edit or recreate an image, please:")
                    st.write("1. Upload an image using the file uploader above")
                    st.write("2. Then use editing commands like:")
                    st.write("   • `/generate edit the image, remove the car`")
                    st.write("   • `/generate recreate this image in cartoon style`")
                    st.write("   • `/generate modify the image, make it sunny`")
                
                st.session_state['messages'].append({
                    'role': 'assistant',
                    'content': 'To edit or recreate an image, please upload one first, then use the /generate command with your editing instructions.'
                })
                st.stop()
            
            else:
                # Regular text-to-image generation
                generation_prompt = prompt
            
            # Clear the pending image after using it for recreation/editing
            if has_image and (is_recreation or is_editing):
                st.session_state.pop('pending_image', None)
            
            with st.spinner(f"Generating image with {image_model}..."):
                try:
                    # Clean and validate the prompt
                    clean_prompt = generation_prompt.strip()
                    
                    # Basic content filtering (expand as needed)
                    blocked_words = ['nude', 'naked', 'nsfw', 'explicit', 'sexual', 'gore', 'violence', 'blood', 'weapon', 'gun', 'knife']
                    if any(word in clean_prompt.lower() for word in blocked_words):
                        error_msg = "⚠️ Your prompt contains content that may violate OpenAI's usage policies. Please try a different prompt."
                        with st.chat_message("assistant"):
                            st.warning(error_msg)
                        st.session_state['messages'].append({
                            'role': 'assistant',
                            'content': error_msg
                        })
                    else:
                        # Generate image using Images API
                        response = client.images.generate(
                            model=image_model,
                            prompt=clean_prompt,
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
                                'caption': f"Generated with {image_model}: {clean_prompt[:50]}{'...' if len(clean_prompt) > 50 else ''}"
                            })
                            
                            # Display the generated image
                            with st.chat_message("assistant"):
                                st.success(f"✅ Image generated successfully with {image_model}!")
                                st.image(
                                    decoded_image, 
                                    caption=f"Prompt: {clean_prompt}", 
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
                    error_str = str(e)
                    
                    # More specific error handling
                    if "image_generation_user_error" in error_str:
                        error_msg = "⚠️ **Content Policy Error**: Your prompt may violate OpenAI's usage policies. Try rephrasing with:\n\n"
                        error_msg += "• More descriptive, positive language\n"
                        error_msg += "• Avoid potentially sensitive topics\n"
                        error_msg += "• Focus on artistic, creative descriptions\n\n"
                        error_msg += "**Example**: Instead of 'scary monster', try 'friendly cartoon character'"
                        
                        with st.chat_message("assistant"):
                            st.warning("Content Policy Issue")
                            st.markdown(error_msg)
                            
                        # Suggest alternative prompts
                        st.info("💡 **Suggested alternatives:**")
                        suggestions = [
                            "a beautiful artistic scene with similar elements",
                            "a creative interpretation in watercolor style",
                            "a modern digital art version with vibrant colors"
                        ]
                        for i, suggestion in enumerate(suggestions, 1):
                            st.write(f"{i}. `/generate {suggestion}`")
                            
                    elif "billing" in error_str.lower() or "quota" in error_str.lower():
                        error_msg = "💳 **Billing Issue**: Your OpenAI account may be out of credits or have billing issues."
                        with st.chat_message("assistant"):
                            st.error(error_msg)
                            st.info("💡 Check your OpenAI account at https://platform.openai.com/account/billing")
                            
                    elif "rate" in error_str.lower() or "limit" in error_str.lower():
                        error_msg = "⏱️ **Rate Limit**: You're making requests too quickly. Please wait a moment and try again."
                        with st.chat_message("assistant"):
                            st.warning(error_msg)
                            st.info("💡 Try again in 10-20 seconds")
                            
                    elif "model" in error_str.lower():
                        error_msg = f"🤖 **Model Error**: There might be an issue with the {image_model} model."
                        with st.chat_message("assistant"):
                            st.error(error_msg)
                            st.info("💡 Try switching to a different model in the sidebar")
                            
                    else:
                        error_msg = f"❌ **Unknown Error**: {error_str}"
                        with st.chat_message("assistant"):
                            st.error(error_msg)
                            st.info("💡 Try rephrasing your prompt or check your internet connection")
                    
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
**Image Editing:**
- Upload an image above the chat input
- Use editing commands like:
  - `/generate edit the image, remove the helicopter`
  - `/generate modify the image, make it sunny`
  - `/generate edit this image, add a rainbow`
  - `/generate change the image, make it nighttime`

**Image Recreation:**
- Upload an image and use:
  - `/generate recreate this image`
  - `/generate recreate this image in cartoon style`

**Image Generation:**
- Use `/generate [your prompt]`
- Example: `/generate a sunset over mountains`

**Text Chat:**
- Just type your message normally
- Context is maintained across messages

**Tips:**
- Be specific in your editing instructions
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