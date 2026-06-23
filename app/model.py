from llama_index.llms.ollama import Ollama
from llama_index.core.llms import ChatMessage
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
from langfuse import get_client,propagate_attributes
from dotenv import load_dotenv
from datetime import datetime
from typing import Any
import os
import json

load_dotenv()
LlamaIndexInstrumentor().instrument()
langfuse = get_client()


first_model = Ollama(
    model=str(os.getenv("OLLAMA_MODEL")),
    base_url="https://ollama.com",
    temperature=0.1,
    context_window=64000,
    json_mode=True,
    headers={
        "Authorization": f"Bearer {os.getenv('OLLAMA_API_KEY')}"
    }
)

fast_model=Ollama(
    model=str(os.getenv("REVIEW_MODEL")),
    base_url="https://ollama.com",
    temperature=0.1,
    context_window=64000,
    json_mode=True,
    headers={
        "Authorization": f"Bearer {os.getenv('OLLAMA_API_KEY')}"
    }
)


def clean_json_response(content: str) -> str:
    content = content.strip()
    if content.startswith("```json"):
        content = content.removeprefix("```json").strip()
    elif content.startswith("```"):
        content = content.removeprefix("```").strip()
    if content.endswith("```"):
        content = content.removesuffix("```").strip()
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and start < end:
        content = content[start:end + 1].strip()
    return content


def query(msg : str,llm,workflow_run_id,tag):
    metadata={
        "workflow_run_id" : workflow_run_id,
        "name/tag" : tag,
    }
    
    with langfuse.start_as_current_observation(
        name=tag,
        as_type="span",
        input=msg,
        metadata=metadata
    ) as observation :
        
    
        with propagate_attributes(
            session_id=workflow_run_id,
            trace_name= f"{datetime.now().hour}:{datetime.now().minute}-{tag}-{workflow_run_id[:4]}",
            metadata=metadata
        ) :
            response = llm.chat([ChatMessage(content = msg)])
        
        observation.update(output=str(response))
    langfuse.flush()
    return response.message.content


def query_json(msg : str,llm,workflow_run_id,tag)-> dict[Any,Any]:
    edit_tag = tag
    while True :
        try :
            response = query(msg=msg,llm=llm,workflow_run_id=workflow_run_id,tag=edit_tag)
            response = clean_json_response(response) #on clean et on load.
            response = json.loads(response)
            break
        except json.JSONDecodeError as e :
            print("\n\nLogging Error :" + e.msg + "\n\n")
            edit_tag="2nd:"+ edit_tag #catcher l'erreur si json non valide et reessayer,(ptet max 2 fois) - on ecrit dans le tag que c'est un deuxieme essai(ou plus->compteur ? ) pour le logging langfuse
            continue
    
    return response
    