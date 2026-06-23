from pathlib import Path
from model import fast_model,first_model,query_json
import pathspec
import os 
import json


"""
Chemin,taille,nombre de lignes,extension + exclusion gitignore + exclusion assets+tests : pdf + dossiers assets/ et dossier tests/ 
"""
def make_inventory(repo_root : str):
    path_root = Path(repo_root)
    os.chdir(path_root)
    print(os.getcwd())
    return list_files(Path("."))



def load_gitignore(spec : bool) -> pathspec.PathSpec | list[str] | None:
    gitignore = Path(".gitignore")
    exclusions = []
    if gitignore.exists() :
        exclusions = gitignore.read_text(
        encoding="utf-8",
        errors="ignore"
    ).splitlines()
    
    else : 
        print("\n\n DEBUG : DONT EXIST \n\n")
    
    
    exclusions.append("assets")
    exclusions.append("*.pdf")
    exclusions.append("test*")
    exclusions.append(".git")
    
    if spec :
        return pathspec.PathSpec.from_lines("gitignore",exclusions)
    else : 
        return exclusions

def is_ignored(path : Path ,repo_root : Path,spec :pathspec.PathSpec) -> bool:
    if spec is None : 
        return False 
    
    file = path.relative_to(repo_root).as_posix()
    return spec.match_file(file)

def line_count(filepath : Path):
    return filepath.read_text().count("\n") +1

def add_file_to_tree(tree : dict,filepath : Path,repo_root : Path,metadata : dict):
    relative_parts = filepath.relative_to(repo_root).parts
    current_children = tree["children"]
    
    for part in relative_parts[:-1]:
        if part not in current_children:
            current_children[part] = {
                "name" : part,
                "type" : "directory",
                "children" : {}
            }
        
        current_children = current_children[part]["children"]
    
    filename = relative_parts[-1]
    current_children[filename] = metadata


def list_files(repo_root : Path) -> dict :
    spec : pathspec.PathSpec = load_gitignore(True) # type: ignore  #on pourrait factoriser la fonction pour renvoyer un tuple et eviter la repetition d'appels,mais pour l'instant pas prioritaire
    healthy_files = {
        "tree" : {
            "name" : repo_root.name or ".",
            "type" : "directory",
            "children" : {}
        },
        "files" : {
            
        }
    }
    for curr_dir,dirnames,filenames in os.walk(repo_root,topdown=True):
        #creer json en verifiant avant assets + tests + gitignore,et en ajoutant les propriétés a la volée (propriétés calculées par des fonctiones utilitaires)
        current_path= Path(curr_dir)
        healthy_dirs = []
        
        
        for dirname in dirnames :
            dir_path = current_path / dirname
            
            if is_ignored(dir_path,repo_root,spec) :
                continue 
            
            healthy_dirs.append(dirname)
        
        dirnames[:] = healthy_dirs
        
        for filename in filenames :
            filepath = current_path / filename
            
            if is_ignored(filepath,repo_root,spec):
                continue
            
            count = line_count(filepath)
            size = filepath.stat().st_size
            relative_path = filepath.relative_to(repo_root).as_posix()
            low_relative_path = relative_path.lower()
            metadata = {
                "name" : filepath.name,
                "path" : relative_path,
                "type" : "file",
                "extension" : filepath.suffix,
                "size" :  size,
                "lines_count" : count ,
                "score" : None,
                "sections" : [],
                "resume" : ""
            }
            
            healthy_files["files"][low_relative_path] = metadata
            add_file_to_tree(healthy_files["tree"],filepath,repo_root,metadata)
    return healthy_files


def terminal_ask(question : str)-> str:
    res = input("\n" + question + "\n")
    return res


def readme_usefulness(database : dict,workflow_id : str) -> str | dict :
    if "readme.md" not in database["files"] or database["files"]["readme.md"]["lines_count"] < 2:
        database["files"]["readme.md"]["resume"] = "No content"
        database["files"]["readme.md"]["score"] = 0
        return "empty"
    else :
        above = True
        if database["files"]["readme.md"]["lines_count"] <= 100 :
            above = False 
        msg = f"""Ta tache est de determiner et evalluer si le readme.md d'une codebase est utile,inutile,ou insuffisant.
        Tu dois classer le README dans une seule de ces categories :
        - "utile"
        - "insuffisant"
        - "inutile"

        Definitions :

        "inutile" :
        - Le README est vide ou presque vide.
        - Il ne contient pas assez d'informations exploitables.
        - Il est hors sujet ou ne correspond pas au projet.

        "insuffisant" :
        - Le README donne quelques informations utiles, mais pas assez pour comprendre correctement le projet.
        - Il est trop centre sur des details techniques sans expliquer le but du projet.
        - Il peut servir de source secondaire, mais pas de base principale.
        - Il est court mais contient des informations utiles.

        "utile" :
        - Le README explique clairement le but du projet.
        - Il decrit au moins partiellement le fonctionnement, l'installation, l'usage ou la structure.
        - Il contient assez d'informations pour aider a produire une documentation pertinente.
        - Il contient une quantité d'information et de profondeur minimale.
        N'hesite pas a etre strict.Ne considere pas un readme utile par ce que tu as peur de faire rater des informations.Utile veut dire complet et exemplaire pour un readme de codebase operationnel
        
        Tu retourneras uniquement un JSON valide sous cette forme :
        
        {{
            "status": "utile | insuffisant | inutile",
            "score" : 0-100,
            "raison" : "",
            "resume" : ""
        }}
        Regles pour le score :
        - 0 a 30 : inutile
        - 31 a 70 : insuffisant
        - 71 a 100 : utile
        
        Dans raison,tu ecris le raisonnement qui t'as mené a tes choix.
        {"Dans resume,ecris un resume complet du readme,uniquement si il etait utile ou insuffisant" if above else "Laisse le champ resume vide"}
        Voila le readme a evaluer : 
        \"\"\"
        {Path(database['files']['readme.md']['path']).read_text("utf-8")}
        \"\"\"
        
        Et voila le debut du json,remplis :
        
        """
        res = query_json(msg=msg,llm=first_model,workflow_run_id=workflow_id,tag="readme-checking")
        
        database["files"]["readme.md"]["score"] = res["score"]
        
        print(f"\n\n DEBUG \n Raison : {res['raison']} \n")
        
        if above and res["status"] == "utile" or res["status"] == "insuffisant":
            database["files"]["readme.md"]["resume"] = res["resume"]
            
        return res
        
    