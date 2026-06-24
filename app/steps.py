"""
Premiere etape poser questions,avec une ou deux requetes reucperer un json du genre,a partir des reponses de l'utilisateur,qu'on envoie au llm :
{
    'taille' : [petite,moyenne,grande],
    'niveau de detail' : [poussé/complexe,high-level,mid-level -> plutot libre],
    'diagramme' : [True/False],
    'format' : [docx,odt,md,txt],
    'Public visé' : ["developpeurs","grand-public/vulgarisation","clients/utilisateurs" -> plutot libre],
    'objectif' : [maintenance,extension,migration,etc etc -> plutot libre],
    'commentaires utilisateurs utiles' : str libre
}

ce meme json sera simplifié et reinjecté a chaque prompt ecrivain
"""
from collections.abc import Callable
from model import query,query_json,first_model
from utils import terminal_ask

async def ask_all_questions(ask_func: Callable)-> dict[str,str]:
    """Poser et recuperer toutes les questions necessaires"""
    response = dict() 
    questions = [
        "Quelle taille pour votre documentation ? Petite, moyenne, grande ?",
        "Quel niveau de detail ? Beaucoup de details (low level), moyen (mid-level), ou une vue plus generale(high-level) ?",
        "Inclure un diagramme mermaid ?",
        "Quel format de sortie ? docx,odt,md,ou txt ?",
        "Qui est le public visé ?",
        "Ya t'il un objectif particulier pour cette documentation ?",
        "Des fichiers/sections a exclure de la documentation ?",
        "Avez vous des precisions a ajouter ?"
    ]
    for question in questions :
        response[question] = ask_func(question)
    
    return response


async def get_json_resume(ask_all_questions:Callable,workflow_run_id : str) -> dict[str,str]: 
    """Fonction qui va recuperer toutes les reponses,va faire un call,puis agreger les reponses dans un json."""
    msg = f"""Voici un json/dictionnaire de questions reponses : f{await ask_all_questions(terminal_ask)}.Transforme le 
    en un dictionnaire abrégé de cette forme a partir des reponses de celui-ci :
    {{
        "taille" : reponses possibles : ["tres petite","petite","moyenne","grande"],
        "niveau de detail" : ["low-level","mid-level","high-level"],
        "diagramme" : "["oui","non"],
        "format" : ["docx","odt","md","txt"],
        "public visé" : "reponse libre mais bien abrégée",
        "objectif" : "reponse libre mais abrégée",
        "Exclusion" : "soit les noms des fichiers,soit une exclusion generale au niveau de la redaction",
        "commentaires" : "reponse libre."
    }}
    Voila le debut,complete le json :
    {{
    """
    res = query_json(msg=msg,llm=first_model,workflow_run_id=workflow_run_id,tag="resuming json user answers") 
    return res 

"""
Step 1 (brainstorm) : 
-> res = get json resume 
step 2 (inventory & planning)
-> database = make_inventory
-> list = get_meaningful_list(readme_usefulness)
-> resuming_meaningful_list(list & database)
-> get plan(database + readme + resume meaningful, +instructions utilisateurs(res)) -> choix user
step 3 (exploring):
-> associer les 2-7 fichiers non associés aux sections(fonction mult_score_resume_associate qui appelle plusieurs fois la fonction one shot)
-> explorer l'ensemble de la codebase et scorer,puis resumer et associer (sauf ceux deja resumés et scorés)
-> quand il y a association,a ce moment la,stocker dans un endroit facile d'acces les fichiers concernés par chaque section
step 4 (writing):
-> faire ecrire chaque section avec les injections de resume
->  
"""

