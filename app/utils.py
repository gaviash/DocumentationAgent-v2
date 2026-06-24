from pathlib import Path
from model import fast_model,first_model,query_json
import pathspec
import os 
import json

SCORE_SEUIL_HAUT = 70
SCORE_SEUIL_BAS = 40

path_bonuses = {
    "src/" : 40,
    "app/" : 40,
    "lib/" : 35,
    "server/": 35,
    "docs/" : 25,
    "routes/" : 25,
    "config/" : 20,
    "scripts/" : 10,
    ".github/" : 20,
}
name_bonuses = {
    "main" : 30,
    "app" : 30,
    "server" : 30,
    "controller" : 25,
    "route" : 25,
    "handler" : 25,
    "service" : 25,
    "manager" : 25,
    "usecase" : 25,
    "repository" : 20,
    "root" : 20,
    "model" : 20,
    "schema" : 20,
    "entity" : 20,
    "config" : 15,
    "settings": 15, 
    "requirements" : 70,
    "Dockerfile" : 70
}

extension_bonuses = {
    ".py" : 10,
    ".ts" : 10,
    ".tsx" : 10,
    ".js" : 10,
    ".jsx" : 10,
    ".go" : 10,
    ".c" : 10,
    ".h" : 10,
    ".java" : 10,
    ".rs" : 10,
    ".toml" : 5,
    ".yml" : 5,
    ".yaml" : 5,
    ".json" : 5,
    "xml" : 5,
    ".md" : 10,
}

name_penalties = {
    "test",
    "asset",
    "generated",
    "lockfile",
    "node_modules",
    "dist",
    "build_output"
}
"""
Chemin,taille,nombre de lignes,extension + exclusion gitignore + exclusion assets+tests : pdf + dossiers assets/ et dossier tests/ 
"""
def make_inventory(repo_root : str):
    path_root = Path(repo_root)
    os.chdir(path_root)
    print(os.getcwd()) # debug
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


def readme_usefulness(database : dict,workflow_id : str) -> str :
    if "readme.md" not in database["files"] :
        return "empty"
    if database["files"]["readme.md"]["lines_count"] < 2:
        database["files"]["readme.md"]["resume"] = "No content"
        database["files"]["readme.md"]["score"] = 0
        return "empty"
    else :
        above = True
        if database["files"]["readme.md"]["lines_count"] <= 100 :
            above = False 
        msg = f"""Ta tache est de determiner et evaluer si le readme.md d'une codebase est utile,inutile,ou insuffisant.
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
        {"Dans resume,ecris un resume complet du readme,uniquement si il etait utile ou insuffisant.Le resume doit etre exhaustif du readme,et contenir un max d'infos." if above else "Laisse le champ resume vide"}
        Voila le readme a evaluer : 
        \"\"\"
        {Path(database['files']['readme.md']['path']).read_text("utf-8")}
        \"\"\"
        
        Et voila le debut du json,remplis :
        
        """
        res = query_json(msg=msg,llm=first_model,workflow_run_id=workflow_id,tag="readme-checking")
        
        database["files"]["readme.md"]["score"] = res["score"]
        
        print(f"\n\n DEBUG \n Raison : {res['raison']} \n")
        
        if above and (res["status"] == "utile" or res["status"] == "insuffisant"):
            database["files"]["readme.md"]["resume"] = res["resume"]
            
        return res["status"]
        
def get_meaningful_list(database : dict,readme_status : str,workflow_id : str) -> dict:
    #func pour gerer le comportement avec le readme
    msg = f"""Ton but est de fournir une liste des 2-7 fichiers les plus coherents parmi l'arborescence ci-dessous.Choisis les fichiers qui vont donner les infos necessaires pour permettre de construire un plan de 
        redaction de documentation de la codebase.Tu reflechis aux fichiers qui permettent de saisir le plus du projet.Des entrypoints api,des fichiers main,etc etc,tu es capable de bien reflechir.
        {handle_usefulness_response(database=database,readme_status=readme_status)}
        
        Voila l'arborescence des fichiers de la codebase :
        
        {json.dumps(database['tree'],indent=2,ensure_ascii=False)}
        
        La sortie que tu dois produire est uniquement un json de cette forme :
        {{
            "num_fichiers":[2-7],
            1 : <chemin>,
            2 : <chemin>,
            etc,pour le nombre de fichier que tu as choisi.
        }}
        
        
        """
    return query_json(msg=msg,llm=first_model,workflow_run_id=workflow_id,tag="choosing_files")


def handle_usefulness_response(database : dict,readme_status : str) -> str | None :
    msg_utile = "le contenu est fiable et qu'il peut servir de base consequente."
    msg_insuffisant = "le contenu est fiable mais manque totalement d'informations."
    if readme_status == "empty" or readme_status == "inutile":
        return "Le readme est vide/n'existe pas/est totalement inutile,ce n'est pas une source de confiance,on ne l'utilise pas."
    elif (readme_status == "utile" or readme_status == "insuffisant") and database["files"]["readme.md"]["resume"] == "":
        return f"Voici le contenu du readme : {Path(database['files']['readme.md']['path']).read_text()},il a été considéré comme {readme_status},donc considere bien que {msg_utile if readme_status == 'utile' else msg_insuffisant}."
    elif (readme_status == "utile" or readme_status == "insuffisant") and database["files"]["readme.md"]["resume"] != "":
        return f"Le readme a été considéré comme {readme_status},donc considere bien que {msg_utile if readme_status == 'utile' else msg_insuffisant}.Son resume se trouve dans l'entree resume de son objet dans l'arborescence"
    
    
def score_resume_associate(database : dict,filepath : str | Path,mode : str): 
    #si mode = full,on fait tout,si mode = associate,on ne refait pas scoring + resume,juste on associe,et si mode = classic,on score et on resume,sans associer.Ex pour les documents d'infos du planner,en mode classique,apres 
    #le planner,en mode full sur tous les fichiers,et les fichiers resumés pour le planner,mais qui n'ont pas pu etre associés par ce que le plan n'existait pas,on relancera en mode associer. 
    return 1


def score(metadata : dict,filepath : Path):
    #location part
    scorer = 0
    folders = filepath.parts[:-1]
    best = 0
    for folder in folders :
        val = path_bonuses.get(folder,0)
        if val > best :
            best = val
    scorer += best 
    
    #name part 
    name = filepath.stem
    scorer += name_bonuses.get(name,0)
    
    #line count part
    count = metadata["lines_count"]
    if count < 3 :
        scorer -= 10
    elif count < 10 :
        scorer += 10
    elif count < 500 :
        scorer += 20
    elif count < 1000 :
        scorer += 10
    elif count < 5000:
        scorer -= 10
    else :
        scorer += 0
    
    #et extension
    scorer += extension_bonuses.get(metadata["extension"],0)
    
    return scorer
   

#fonction utilitaire d'exploration et de scoring,qui peut prendre une liste de fichiers specifiques en argument,ou aucun(dans ce cas la on explorera tout le repo),
# et resume + score ces fichiers, evitant de rescorer ou de re-resumer ceux deja résumés et scorés

#il manque plein de petites optimisations,comme le fait que des fois,beaucoup d 'infos pas forcement necessaires sont passées en chemin (ex les metadat entieres sont passées alors qu'on a besoin que de line_count),
#l'optimisation de la modularisation des fonctions.Je decoupe bien en petits morceaux mes taches,mais est ce que je les decoupe bien(au bon endroit) ? etc etc