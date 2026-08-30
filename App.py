import os
import json
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
MODEL_NAME = "llama3-8b-8192"
MEMORY_FILE = "user_memory.json"

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
                "key": {"type": "string", "description": "Category (e.g., 'name', 'interests', 'tone')"},
                "value": {"type": "string", "description": "Specific detail to remember"}
            },
            "required": ["key", "value"]
        }
    }
}]

# Chat Interface
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    if isinstance(msg, dict) and msg.get("role") in ["user", "assistant"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if user_input := st.chat_input("Type a message..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    current_mem = load_memory()
    system_prompt = {
        "role": "system",
        "content": (
            "You are a personalized AI assistant. Adapt your behavior to the user's stored preferences.\n\n"
            f"STORED KNOWLEDGE:\n{json.dumps(current_mem, indent=2)}\n\n"
            "INSTRUCTIONS:\n"
            "1. If the user shares personal facts, use the `update_memory` tool immediately.\n"
            "2. DO NOT use LaTeX or heavy formatting. Write math simply (e.g., a^2, x/y)."
        )
    }

    api_messages = [system_prompt] + [
        m for m in st.session_state.messages 
        if isinstance(m, dict) and m.get("role") in ["user", "assistant", "system", "tool"]
    ]

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=api_messages,
                    tools=tools,
                    tool_choice="auto"
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
                        model=MODEL_NAME,
                        messages=api_messages
                    )
                    reply = final_res.choices[0].message.content
                else:
                    reply = response_message.content

                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

            except Exception as e:
                st.error(f"Error: {e}")
              
