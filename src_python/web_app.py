import gradio as gr
import os
import json
from rag_engine import get_rag_chain

# Initialize the RAG chain
print("Loading Jarvis Engine for Web...")
chain = get_rag_chain()

def process_query(message, history):
    """
    Process the user query through the RAG chain and split the response.
    """
    try:
        full_response = chain.invoke(message)
        
        # Parse the response using our delimiters
        if "--- JARVIS RESPONSE ---" in full_response:
            parts = full_response.split("--- JARVIS RESPONSE ---")
            reasoning = parts[0].replace("--- INTERNAL REASONING ---", "").strip()
            jarvis_speech = parts[1].strip()
            return jarvis_speech, reasoning
        else:
            return full_response, "No structured reasoning available."
            
    except Exception as e:
        return f"Error: {e}", str(e)

# Custom CSS for a premium look
custom_css = """
.gradio-container {
    background-color: #f0f2f5;
    font-family: 'Inter', sans-serif;
}
.main-header {
    text-align: center;
    color: #1a365d;
    margin-bottom: 2rem;
}
.reasoning-box {
    background-color: #ffffff;
    border-radius: 8px;
    padding: 15px;
    border-left: 5px solid #3182ce;
}
"""

with gr.Blocks(title="Jarvis - Truck Configurator") as demo:
    gr.Markdown(
        """
        # 🚛 Jarvis: AI Truck Configuration Specialist
        ### Expert Advice | Engineering Constraints | Real-World EPA Data
        """
    )
    
    with gr.Row():
        # Left Column: Chat Interface
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(label="Jarvis Conversation", height=500)
            msg = gr.Textbox(
                label="Your Request",
                placeholder="e.g., 'I need a workhorse for my farm' or 'Tell me about the 2017 RAM 2500'",
                show_label=True
            )
            with gr.Row():
                clear = gr.Button("Clear History")
                submit = gr.Button("Send to Jarvis", variant="primary")

        # Right Column: Internal Reasoning & Metadata
        with gr.Column(scale=1):
            reasoning_output = gr.Code(
                label="Jarvis's Internal Reasoning (JSON)",
                language="json",
                interactive=False,
                lines=15
            )
            gr.Markdown(
                """
                ### 🛠️ System Status
                - **Model**: Mistral 7B (via Ollama)
                - **Data**: EPA + Engineering Manual
                - **Persona**: Senior Specialist (Jarvis)
                """
            )

    def respond(message, chat_history):
        bot_message, reasoning = process_query(message, chat_history)
        chat_history.append((message, bot_message))
        return "", chat_history, reasoning

    # Event handlers
    submit.click(respond, [msg, chatbot], [msg, chatbot, reasoning_output])
    msg.submit(respond, [msg, chatbot], [msg, chatbot, reasoning_output])
    clear.click(lambda: None, None, chatbot, queue=False)

if __name__ == "__main__":
    # Launch the web app
    demo.launch(
        server_name="127.0.0.1", 
        server_port=7860, 
        share=False, 
        css=custom_css
    )

