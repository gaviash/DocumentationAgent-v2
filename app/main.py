from model import first_model,query,query_json
from steps import get_json_resume,ask_all_questions
from uuid import uuid4
import asyncio

async def main():
    workflow_id = str(uuid4())
    print(str(await get_json_resume(ask_all_questions=ask_all_questions,workflow_run_id=workflow_id)))
    


asyncio.run(main())