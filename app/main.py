from model import first_model,query,query_json
from steps import get_json_resume,ask_all_questions
from utils import make_inventory,readme_usefulness
from uuid import uuid4
import asyncio
import json

async def main():
    workflow_id = str(uuid4())
    database = make_inventory(r"C:\Users\Gavriel.Myara\Desktop\DocumentationAgentv2\app\process\little_agent")
    res = readme_usefulness(database=database,workflow_id=workflow_id)
    print(f"\n Readme results : \n {json.dumps(res,indent=2,ensure_ascii=False) if isinstance(res,dict) else res}\n")
    print(f"Database : \n {json.dumps(database['files'],indent=2)}")

asyncio.run(main())