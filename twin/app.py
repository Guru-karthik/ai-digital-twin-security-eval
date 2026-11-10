from openai import OpenAI
from agent import run_chat
from backends import make_backend
from config import load_config
from context import build_system_prompt
from dispatcher import Dispatcher
from runlog import RunLogger
from styles import CSS, JS, EXAMPLES
from dotenv import load_dotenv
import gradio as gr

load_dotenv(override=True)

config = load_config()
client = OpenAI()
system_prompt = build_system_prompt()
backend = make_backend(config)
logger = RunLogger(path=config.log_path, config=config)


def chat(message, history):
    dispatcher = Dispatcher(backend, config)  # per request: no shared per-request state
    return run_chat(client, config, system_prompt, dispatcher, message, history, logger)


if __name__ == "__main__":
    gr.ChatInterface(
        chat,
        examples=EXAMPLES,
        title="Digital Twin",
        description="Talk to my AI twin about my career. This is an AI assistant, not the person.",
        chatbot=gr.Chatbot(show_label=False),
    ).launch(css=CSS, js=JS, theme=gr.themes.Base())
