import os
import json
import base64
import streamlit as st
from openai import OpenAI

# Page UI
st.set_page_config(page_title="My AI", page_icon="🤖")
st.title("🤖 Personal AI Assistant")

# API Setup
API_KEY = "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"
client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.groq.com/openai/v1",
    timeout=120.0
)

# Text and Vision Models
TEXT_MODEL = "openai/gpt-oss-120b"
VISION_MODEL = "qwen/qwen3.6-27b"
MEMORY_FILE = "user_memory.json"

# Image Encoding Function
def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.read()).decode('utf-8')

# Memory Functions
def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f)

tools = [{
    "type": "function",
    "function": {
        "name": "update_memory",
        "description": "Save or update a fact, preference, or conversational habit about the user.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Category"},
                "value": {"type": "string", "description": "Detail to remember"}
            },
            "required": ["key", "value"]
        }
    }
}]

# Chat Interface
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous chat messages
for msg in st.session_state.messages:
    if isinstance(msg, dict) and msg.get("role") in ["user", "assistant"]:
        with st.chat_message(msg["role"]):
            # If the user message is a list (contains image), just show the text part
            if isinstance(msg["content"], list):
                st.markdown(msg["content"][0]["text"])
                st.caption("📷 Image attached")
            else:
                st.markdown(msg["content"])

# Image Uploader (New Feature!)
uploaded_image = st.file_uploader("Upload an image (optional)", type=["jpg", "jpeg", "png"])

if user_input := st.chat_input("Type a message..."):
    # Check if an image was uploaded
    if uploaded_image:
        base64_image = encode_image(uploaded_image)
        # Format required for vision models
        message_content = [
            {"type": "text", "text": user_input},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            }
        ]
        active_model = VISION_MODEL
    else:
        message_content = user_input
        active_model = TEXT_MODEL

    # Save to history and display
    st.session_state.messages.append({"role": "user", "content": message_content})
    with st.chat_message("user"):
        st.markdown(user_input)
        if uploaded_image:
             st.image(uploaded_image, width=200)

    current_mem = load_memory()
    system_prompt = {
        "role": "system",
        "content": (
            "You are a personalized AI assistant. Adapt your behavior to the user's stored preferences.\n\n"
            f"STORED KNOWLEDGE:\n{json.dumps(current_mem, indent=2)}\n\n"
            "INSTRUCTIONS:\n"
            "1. If the user shares personal facts, use the `update_memory` tool.\n"
            "2. DO NOT use LaTeX or heavy formatting."
        )
    }

    api_messages = [system_prompt] + [
        m for m in st.session_state.messages 
        if isinstance(m, dict) and m.get("role") in ["user", "assistant", "system", "tool"]
    ]

    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            try:
                response = client.chat.completions.create(
                    model=active_model,
                    messages=api_messages,
                    tools=tools if not uploaded_image else None, # Tools sometimes conflict with vision
                    tool_choice="auto" if not uploaded_image else None
                )
                response_message = response.choices[0].message

                if response_message.tool_calls:
                    for tool_call in response_message.tool_calls:
                        if tool_call.function.name == "update_memory":
                            args = json.loads(tool_call.function.arguments)
                            key = args.get("key")
                            value = args.get("value")

                            current_mem[key] = value
                            save_memory(current_mem)
                            st.toast(f"🧠 Remembered: {key} -> {value}")

                            st.session_state.messages.append(response_message)
                            st.session_state.messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": "update_memory",
                                "content": "Memory saved."
                            })

                    updated_system_prompt = {
                        "role": "system",
                        "content": system_prompt["content"].replace(
                            json.dumps(load_memory(), indent=2),
                            json.dumps(current_mem, indent=2)
                        )
                    }
                    
                    api_messages = [updated_system_prompt] + [
                        m for m in st.session_state.messages 
                        if isinstance(m, dict) or hasattr(m, 'role')
                    ]

                    final_res = client.chat.completions.create(
                        model=active_model,
                        messages=api_messages
                    )
                    reply = final_res.choices[0].message.content
                else:
                    reply = response_message.content

                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

            except Exception as e:
                st.error(f"Error: {e}")
                
