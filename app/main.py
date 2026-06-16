from model import first_model,query
from uuid import uuid4
import asyncio

async def main():
    workflow_id = str(uuid4())
    res = await query(
        "Fais moi un resume sur leo messi,structuré en json suivant : enfance,formation,performance,club et impact.Profondeur de json 1,pas d'enfants.Voila le debut du json a remplir/completer : {",
        first_model,workflow_id,
        "resumé")
    print(res)


asyncio.run(main())