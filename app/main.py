from model import first_model,query,query_json
from steps import get_json_resume,ask_all_questions,write_all_sections
from utils import make_inventory,readme_usefulness,get_meaningful_list,score_calibration,score_resume_associate,create_plan,discover_and_adapt_environment,classify_all_docs
from uuid import uuid4
from pathlib import Path
from copy import deepcopy
import asyncio
import json

"""
def classify_all_docs(database:dict,sections :dict,meaningful_list :dict,workflow_id : str): #apres le plan
    for file in database["files"]:
        strpath = database["files"][file]["path"]
        if strpath in meaningful_list.values() or file == "readme.md":
            
            database = score_resume_associate(database=database,sections=sections,filepath=Path(strpath),mode="associate",workflow_run_id=workflow_id)
"""

async def main():
    workflow_id = str(uuid4())
    database = make_inventory(r"C:\Users\Gavriel.Myara\Desktop\DocumentationAgentv2\app\process\little_agent")
    pure_database = deepcopy(database)
    print("\nInventory fait\n")
    questions = get_json_resume(ask_all_questions=ask_all_questions,workflow_run_id=workflow_id)
    readme_status = readme_usefulness(database=database,workflow_id=workflow_id)
    print(f"\nreadme ingéré : {readme_status}")
    
    #res = readme_usefulness(database=database,workflow_id=workflow_id)
    #print(f"\n Readme results : \n {json.dumps(res,indent=2,ensure_ascii=False) if isinstance(res,dict) else res}\n")
    #print(f"\n\n {json.dumps(get_meaningful_list(database=database,readme_status=res,workflow_id=workflow_id),indent=2,ensure_ascii=False)}")
    #print(f"Database : \n {json.dumps(score_calibration(database)['files'],indent=2)}")
    #database = score_resume_associate(database=database,filepath=Path("app/main.py"),mode="resume",workflow_run_id=workflow_id)
    #print(f"Metadata : {json.dumps(database['files']['app/main.py'],indent=2,ensure_ascii=False)}")
    
    meaningful_list = get_meaningful_list(database=database,answers=questions,workflow_id=workflow_id)
    print(f"Liste récupérée :\n {json.dumps(meaningful_list,indent=2,ensure_ascii=False)}")
    
    database,plan = create_plan(
        database=database,
        user_answers=questions,
        readme_status=readme_status,
        meaningful_files=meaningful_list,
        workflow_run_id=workflow_id
    )
    
    print(f"Plan créé : \n {json.dumps(plan,indent=2,ensure_ascii=False)}")
    #Path("plan.json").write_text(json.dumps(plan,indent=2,ensure_ascii=False),encoding="utf-8")
    #plan = json.loads(Path("plan.json").read_text(encoding="utf-8"))
    discover_and_adapt_environment(pure_database=pure_database,sections=plan,workflow_run_id=workflow_id)
    classify_all_docs(database=database,pure_database=pure_database,sections=plan,meaningful_list=meaningful_list,workflow_id=workflow_id)
    write_all_sections(sections=plan,database=database,pure_database=pure_database,answers=questions,workflow_run_id=workflow_id)
    #print(f"Database : {json.dumps(database['files'],indent=2,ensure_ascii=False)}\n\n Sections : {database['sections']}")
    
    
asyncio.run(main())
