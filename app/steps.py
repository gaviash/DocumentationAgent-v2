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

def ask_all_questions(ask_func: Callable)-> dict:
    """Poser et recuperer toutes les questions necessaires"""
    response = dict() 
    questions = [
        "Quelle taille pour votre documentation ? Petite, moyenne, grande ?",
        "Quel niveau de detail ? Beaucoup de details (low level), moyen (mid-level), ou une vue plus generale(high-level) ?",
        "Inclure un diagramme mermaid ?",
        "Quel format de sortie ? docx,odt,md,ou txt ?",
        "Qui est le public visé ?"
    ]
    for question in questions :
        response[question] = ask_func(question)
    
    return response


def get_json_response(ask_all_questions:Callable) -> dict: 
    """Fonction qui va recuperer toutes les reponses,va faire un call,puis agreger les reponses dans un json."""