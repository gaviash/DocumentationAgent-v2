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
from model import query,query_json,first_model,fast_model
from utils import terminal_ask
from pathlib import Path
from merm import render_to_file
from resvg_py import svg_to_bytes
from uuid import uuid4
import pypandoc
import json
import re

def ask_all_questions(ask_func: Callable)-> dict[str,str]:
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


def get_json_resume(ask_all_questions:Callable,workflow_run_id : str) -> dict[str,str]: 
    """Fonction qui va recuperer toutes les reponses,va faire un call,puis agreger les reponses dans un json."""
    msg = f"""Voici un json/dictionnaire de questions reponses : f{ask_all_questions(terminal_ask)}.Transforme le 
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


def write_section(section : str,doc_list : list[str],database_files : dict,pure_database : dict,filtered_answers : dict,workflow_run_id : str)-> str:
    inject = ""
    for doc in doc_list:
        if doc != "tree" :
            inject += f"Fichier : {doc}\n\n Resume : {database_files[doc]['resume']}.\n"
        else :
            inject += f"Voila l'arborescence du reprtoire :  \n {json.dumps(pure_database['tree'])}"
            
    msg = f"""
    Tu es un assistant documentaire ecrivain qui doit ecrire la section d'une documentation.
    Voila le plan de la section que tu vas écrire :
    {section} 
    Et voila les documents necessaires :
    \"\"\"
    {inject}
    \"\"\"
    Enfin,voila des precisions sur la documentation voulue :
    {json.dumps(filtered_answers,indent=2,ensure_ascii=False)}.
    
    Quelques regles a respecter :
    -Pour la longueur de ton texte,refere toi a ton plan de section.Reste quand meme sur un texte relativement long,on parle quand meme d'une documentation.
    -Utilise un ton professionnel mais un texte clair et explicatif.Ton texte reste sur du texte explicatif,dense et concis.
    -Suis totalement ton plan en ce qui concerne l'ecriture.Puis,si ce que dit le plan est totalement respecté,tu peux ajouter des touches personnelles,si elles restent dans la direction du plan,ou si elles apportent
    quelque chose au texte.
    -Le but n'est pas de repeter mecaniquement le plan,mais de partir du plan pour rediger la section finale.
    -Ecris avec une belle mise en page markdown,propre,lisible,sans trop de titres partout,juste ce qu'il faut.Si besoin tu peux integrer des snippets/blocs de code.
    -N'invente rien,aucune api,aucune variable,comportement,fonction,ou quelconque element sur lequel tu n'as pas d'informations.
    -Ne te repete pas.Apporte quelque chose de nouveau a chaque phrase.Pas besoin de faire des longueurs inutilement.
    -Quand une information serait utile a verifier,ou a creuser pour l'utilisateur(ex : verifier un endpoint,un comportement d'une fonction,etc),precise la reference au fichier
    de tes informations. 
    -Commence ta section par le titre de la section.
    -Ne mets des diagrammes que si c'est necessaire/apporte quelque chose,ou si c'est inclus dans le plan.
    -Tu écris tes sections toujours en francais.
    """
    text = query(msg=msg,llm=first_model,workflow_run_id=workflow_run_id,tag="writing")
    return text
    
def write_all_sections(sections : dict,database : dict,pure_database : dict ,answers : dict,workflow_run_id : str):
    filtered_answers = {
        "niveau de detail" : answers["niveau de detail"],
        "public visé" : answers["public visé"],
    }
    
    for i in range(1,sections["nombre sections"]+1) :
        text = write_section(sections[str(i)],database["sections"][i],database_files=database['files'],pure_database=pure_database,filtered_answers=filtered_answers,workflow_run_id=workflow_run_id)
        Path(f"../partie_{i}.md").write_text(text,encoding="utf-8")
    
def convert_to_docx(section_number : int,workflow_run_id : str): 
    #potentiellement rajouter des arguments pour avoir telle ou telle conversion,etc.
    #Arguments pour donner un reference doc precis (changer la mise en page)
    detect_export_mermaid(section_number=section_number,workflow_run_id=workflow_run_id)
    pypandoc.convert_file(
        source_file=[f"../partie_{i}.md" for i in range(1,section_number+1)],
        to="docx",
        format="markdown+pipe_tables+fenced_code_blocks+fenced_divs+smart",
        outputfile=Path("../documentation.docx"),
        extra_args= [
            "--toc",
            "--reference-doc=../reference-doc.docx",
            "--resource-path=../"
        ]
    )
    pass

def convert_to_odt(section_number : int,workflow_run_id : str):
    detect_export_mermaid(section_number=section_number,workflow_run_id=workflow_run_id)
    pypandoc.convert_file(
        source_file=[f"../partie_{i}.md" for i in range(1,section_number+1)],
        to="odt",
        format="markdown+pipe_tables+fenced_code_blocks+fenced_divs+smart",
        outputfile=Path("../documentation.odt"),
        extra_args= [
            "--toc",
            "--reference-doc=../reference-doc.odt",
            "--resource-path=../"
        ]
    )

def md_export(section_number : int):
    out = Path("../documentation.md")
    with out.open("w",encoding="utf-8") as output :
        for i in range(1,section_number+1):
            output.write(Path(f"../partie_{i}.md").read_text(encoding="utf-8"))
            output.write("\n\n")
            
def export(format : str,section_number : int,workflow_run_id : str):
    match format :
        case "docx" :
            convert_to_docx(section_number=section_number,workflow_run_id=workflow_run_id)
        case "md" :
            md_export(section_number=section_number)
        case "odt" :
            convert_to_odt(section_number=section_number,workflow_run_id=workflow_run_id)


def detect_export_mermaid(section_number : int,workflow_run_id : str):
    pattern_re = re.compile(
    r"```[ \t]*mermaid[^\n]*\n(?P<content>.*?)\n```",
    re.DOTALL | re.IGNORECASE,
)
    for i in range(1,section_number+1):
        detect_return_mermaid(section_to_analyze=i,diagram_pattern=pattern_re,workflow_run_id=workflow_run_id)

def detect_return_mermaid(section_to_analyze : int,diagram_pattern : re.Pattern,workflow_run_id : str):
    #detection d'un diagramme, -> generation d'un uuid, -> rendu d'un svg avec cet uuid en nom,et remplacement du diagramme dans le fichier par une reference vers le fichier rendu.
    doc_uuid = ""
    section = Path(f"../partie_{section_to_analyze}.md")
    text = section.read_text(encoding="utf-8").strip()
    for match in reversed(list(diagram_pattern.finditer(text))):
        print("match trouvé !")
        doc_uuid = uuid4()
        content = match.group("content").strip()
        content = upgrade_and_fix_diagram(content=content,workflow_run_id=workflow_run_id)
        render_to_file(content,f"../{doc_uuid}.svg")
        png_bytes = svg_to_bytes(Path(f"../{doc_uuid}.svg").read_text(encoding="utf-8"))
        Path(f"../{doc_uuid}.png").write_bytes(png_bytes)
        text = text[:match.start()] + f"![Diagramme Mermaid]({doc_uuid}.png)" + text[match.end():]
    section.write_text(text,encoding="utf-8")
    #iteration,generation(cleaner/stripper la chaine trouvée) et replace sur le match trouvé

def upgrade_and_fix_diagram(content : str,workflow_run_id : str):
    msg = f"""
    Tu es un assistant design pour diagrammes mermaid.Ton but est de transformer/ameliorer les diagrammes que tu recois.Tu dois eviter/corriger toute erreur
    de casse/syntaxe,ameliorer le visuel,le placement,eviter que les elements se marchent dessus,et rendre le diagramme comprehensible et aéré.
    Voila le diagramme :
    {content}
    
    Voici quelques regles a respecter :
    -Fais particulierement attention a la syntaxe.Pas de syntaxe trop compliquée, on veut eviter la casse.
    -Dans le diagramme,déclare chaque nœud dans un seul subgraph et place les flèches entre sous-graphes après leurs déclarations,
    sans réutiliser un même nœud comme membre de plusieurs blocs.N'utilise des subgraph que pour regrouper au moins deux nœuds différents ;
    si un groupe ne contient qu’un seul nœud, supprime le subgraph et garde seulement le nœud.
    -Ne duplique jamais le nom d’un subgraph et le nom de son unique nœud.
    -Rends le visuel aéré,bien organisé,tout en faisant en sorte que rien ne se marche dessus visuellement.
    -Si besoin est,tu peux reduire la quantité de texte,pour eviter que le diagramme soit trop chargé.
    -Rends le plus attractif/moderne a l'oeil,il ne faut pas qu'il soit fade.
    -fais des schémas visuels sobres : nœuds courts de 1 à 6 mots, chemins de fichiers et détails techniques dans le texte autour, flèches qui ne se marchent pas dessus et pas trop nombreuses,
    labels courts, flowchart LR pour l’architecture, et évite de mélanger runtime, configuration et déploiement dans le même graphe, 
    sauf si c’est indispensable.
    -N'ajoute pas de theme.
    -Ajoute une configuration Mermaid init avec nodeSpacing 70, rankSpacing 90 et diagramPadding 30 pour éviter que les nœuds soient collés.Ajoute le necessaire
    pour eviter que le texte marche sur les noeuds,et vice-versa.
    -Réponds uniquement avec le diagramme Mermaid brut, sans bloc Markdown.
    """
    return query(msg=msg,llm=fast_model,workflow_run_id=workflow_run_id,tag="improving diagram")


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

