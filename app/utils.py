from pathlib import Path
from model import fast_model,first_model,query_json
import pathspec
import os 
import json

SCORE_SEUIL_HAUT = 70
SCORE_SEUIL_BAS = 40

path_bonuses = {
    "src" : 40,
    "app" : 40,
    "lib" : 35,
    "server": 35,
    "docs" : 25,
    "routes" : 25,
    "config" : 20,
    "scripts" : 10,
    ".github" : 20,
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
        
def get_meaningful_list(database : dict,workflow_id : str) -> dict:
    msg = f"""Ton but est de fournir une liste des 2-8 fichiers les plus coherents parmi l'arborescence ci-dessous.Choisis les fichiers qui vont donner les infos necessaires pour permettre de construire un plan de 
        redaction de documentation de la codebase.Tu reflechis aux fichiers qui permettent de saisir le plus du projet.Des entrypoints api,des fichiers main,etc etc,tu es capable de bien reflechir.
        Tu ne dois pas inclure le readme dans tes fichiers coherents-utiles,il est deja pris en compte.
        
        Voila l'arborescence des fichiers de la codebase :
        
        {json.dumps(database['tree'],indent=2,ensure_ascii=False)}
        
        La sortie que tu dois produire est uniquement un json de cette forme :
        {{
            "num_fichiers":[2-8],
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

def discover_and_adapt_environment(): #remplit des metadata dans la database a propos de la codebase -> stack du projet et choix des listes de bonus
    #malus pour le score,(ces listes détaillées seront détaillés et crees par codex,pour ne rien oublier)
    #A decider si la decouverte de la stack doit se faire par code ou par llm call.Si c'est par llm call,utiliser un modele puissant,pour qu'il puisse donner
    #un max de regles coherentes.
    pass


def classify_all_docs(database:dict,sections :dict,meaningful_list :dict,workflow_id : str): #apres le plan
    for file in database["files"]:
        strpath = database["files"][file]["path"]
        if strpath in meaningful_list or file == "readme.md":
            database = score_resume_associate(database=database,sections=sections,filepath=Path(strpath),mode="associate",workflow_run_id=workflow_id)
        else :
            database = score_resume_associate(database=database,sections=sections,filepath=Path(strpath),mode="full",workflow_run_id=workflow_id)
    #avant le score,on recupere l'environnement(fonction discovery)
    #a la fin (une sorte de finally),on associe aussi l'arborescence.
    return database
    
        
    
def score_resume_associate(database : dict,sections : dict,filepath : Path,mode : str,workflow_run_id : str)-> dict: 
    #si mode = full,on fait tout,si mode = associate,on ne refait pas scoring + resume,juste on associe,et si mode = classic(finalement pas implementé),on score et on resume,sans associer.Ex pour les documents d'infos du planner,en mode classique,apres 
    #le planner,en mode full sur tous les fichiers,et les fichiers resumés pour le planner,mais qui n'ont pas pu etre associés par ce que le plan n'existait pas,on relancera en mode associer.mode resumé on resume uniquement 
    if mode == "resume" :
        if database['files'][filepath.as_posix().lower()]["resume"] != "" :
            return database
        
        res = resume(filepath=filepath,workflow_run_id=workflow_run_id)
        print(f"\nResume : {json.dumps(res,indent=2,ensure_ascii=False)}\n")
        database["files"][filepath.as_posix().lower()]["resume"] = res["resume"]
        return database
    elif mode == "associate" :
        sidekicks = associate(database=database,sections=sections,filepath=filepath,workflow_run_id=workflow_run_id)
        database["files"][filepath.as_posix().lower()]["sections"] = sidekicks
        for i in sidekicks :
            database["sections"][i].append(filepath.as_posix().lower())
        return database
    elif mode == "full":
        #score & resume & associate.On associe uniquement les fichiers qui ont un score superieur au seuil.On associe en append la liste de la section concernée : database["sections"][num_section].append(chemin)
        pass
        
    return {}

def resume(filepath : Path,workflow_run_id : str):
    print(f"\nEn train de resumer {filepath.as_posix().lower()} \n")
    msg = f"""
    Tu es un assistant documentaire,et ta tache est de resumer des fichiers de code pour raccourcir le contenu et fournir les informations necessaires.
    Voici le document :
    \"\"\"
    {filepath.read_text(encoding="utf-8")}
    \"\"\"
        
    Voici quelques regles a respecter :
    -Le résumé ne doit pas contenir d'invention,ni de suppositions hallucinées.
    -Le résumé doit dire en premier ce qu'est le fichier/document,puis developper.
    -Le résumé doit etre complet : le but est de raccourcir la comprehension d'un fichier de code,tout en restant exhaustif et fidele
    -Le résumé est compact et dense au niveau de la formulation.On evite un maximum de phrases et formulations inutiles.On garde seulement l'utile et le concret.
    -Il faut inclure un maximum d'infos concernant le code,etre exhaustif,et ne pas avoir peur d'ecrire un plus long texte,sans retomber dans la paraphrase ou du texte pour ne rien dire.Tu peux inclure des snippets de code si ca aide a la comprehension
    il faut que ce soit bien documenté,et bien détaillé,mais juste ce qu'il faut.
        
    Tu repondras sous la forme d'un bloc json comme ci dessous,et uniquement avec ce bloc :
    {{
        "resume" : <resume> 
    }}
    Voila le debut du json,remplis :
    """
    return query_json(msg=msg,llm=first_model,workflow_run_id=workflow_run_id,tag="resume")

def associate(database : dict,sections : dict,filepath : Path,workflow_run_id : str)-> list[int]:
    print(f"\n En train d'associer {filepath.as_posix()}")
    metadata = database['files'][filepath.as_posix().lower()]
    msg =f"""
    Tu es un assistant documentaire,et ta tache est d'associer un document a un ou plusieurs sections d'une documentation,en fonction de son résumé et de ses metadata.
    
    Voici le document :
    \"\"\"
    Resumé : {metadata['resume']}
    Nombre de lignes : {metadata["lines_count"]}
    Chemin et nom : {metadata['path']}
    \"\"\"
    
    Voici les sections du plan :
    \"\"\"
    {json.dumps(sections,indent=2,ensure_ascii=False)}
    \"\"\"
    
    Voici quelques regles a respecter :
    -Tu dois associer le document a la ou les sections qu'il va documenter le mieux
    -N'associe un document a plusieurs sections que si le documents va reellement servir aux deux sections.Si il y a des informations dans un document
    qui sont partagées dans deux sections par exemple
    -Tu repondras sous la forme d'un bloc json comme ci desosus,et uniquement avec ce bloc,sans modifications,sans changement,
    et surtout,sans guillemets autour de la liste : 
    {{
        "section" : [<numero_de_section>,<numero_de_section>,etc]
    }}
    Voila le debut du json,remplis : 
    
    """
    section = query_json(msg=msg,llm=first_model,workflow_run_id=workflow_run_id,tag="associating")
    print(f"Association a {section['section']}")
    return section["section"]
    
    
def create_plan(database : dict,user_answers : dict ,readme_status : str ,meaningful_files : dict ,workflow_run_id : str) :
    #preciser dans le prompt qu'il ya quelques fichiers resumés dans l'arbre pour l'aider a comprendre,et utiliser handle usefulness pour injecter le readme.
    #il doit donner trois choix d'approches(a voir)
    for i in range(1,meaningful_files["num_fichiers"]+1):
        filepath = Path(meaningful_files[str(i)])
        database = score_resume_associate(database=database,sections = {},filepath=filepath,mode="resume",workflow_run_id=workflow_run_id)
        database["files"][filepath.as_posix().lower()]["score"] = 100 #on met a 100 le score des fichiers qui ont étés choisis
    
    answers = user_answers.copy()
    answers.pop("format")
    msg = f"""
    Tu es un agent planificateur dont le but est de proposer un plan complet dans l'optique de rediger une documentation.
    Voila l'aborescence de la codebase,avec des metadata,et les resume de certains fichiers,pour t'aider a comprendre le projet :
    {handle_usefulness_response(database=database,readme_status=readme_status)}
    Arborescence : 
    {json.dumps(database['tree'],indent=2,ensure_ascii=False)}
    Preferences de l'utilisateur pour la documentation : 
    {json.dumps(answers,indent=2,ensure_ascii=False)}
    Regles a absolument respecter :
    - Une petite documentation tourne autour de 3-4 sections,une moyenne autour de 5,6,7 et une grande 5,6,7 ou plus.
    - Tu dois proposer une approche de plan détaillée
    - Tu dois suivre les preferences de l'utilisateur
    - Tu dois proposer un plan sans blabla,sans phrase inutile,dense,mais complet et assez long
    - Ton plan de documentation est segmenté en sections (exemple : introduction,section 1 : endpoints,etc etc)
    - Le plan ne doit pas contenir de sections inutiles,qui n'auront pas assez de contenu,ou qui ne sont pas pertinents.
    - Le contenu de chaque section doit etre précisé clairement,plusieurs phrases.Qu'est ce que doit expliquer la section ? De quoi parlera t-elle,precisement ? etc etc
    - Tu dois reellement prevoir un plan tres complet,détaillé,qui,une fois donné a quelqu'un d'autre pourra lui permettre d'ecrire la documentation
    - Les sections doivent etre détaillées et denses.Sois bavard sur les descriptions de section,n'hesite pas a preciser ce qui doit etre dedans,etc
    - Les sections doivent eviter de se marcher dessus sur les sujets.Chaque section doit aborder un domaine,qui n'est pas du tout abordable dans une autre.
    Ex : ne pas mettre une section Deploiement docker,une section configuration variables env,ET une section installation et deploiement local.C'est beaucoup trop repetitif.Compacte tout en une seule "Configuration,variables env et deploiement"
    Suis ce principe sur tous les sujets.
    Chaque ecrivain n'aura acces qu'aux informations de sa propre section,donc ne melange pas les sujets.
    - Tu repondras sous la stricte forme d'un objet json de la forme qui suit :
    {{
        "nombre sections" : x,
        "1": "nom section 1 : plan de la section 1 détaillé",
        "2" : "nom section 2 : plan de la section 2 détaillé",
        etc etc
    }}
    Complete le json :
    
    """
    sections = query_json(msg=msg,llm=first_model,workflow_run_id=workflow_run_id,tag="planning")
    database['sections'] = {i:[] for i in range(1,sections["nombre sections"]+1)}
    return (database,sections)

def score(metadata : dict,filepath : Path):
    #location part
    scorer = 0
    folders = filepath.parts[:-1]
    #print(folders)
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



def score_calibration(database : dict): # fonction de test qui calcule le score de tous les fichiers
    for file in database["files"] :
        sc = score(database["files"][file],Path(database["files"][file]["path"]))
        #print(sc)
        database["files"][file]["score"] = sc
    return database
#fonction utilitaire d'exploration et de scoring,qui peut prendre une liste de fichiers specifiques en argument,ou aucun(dans ce cas la on explorera tout le repo),
# et resume + score ces fichiers, evitant de rescorer ou de re-resumer ceux deja résumés et scorés

#il manque plein de petites optimisations,comme le fait que des fois,beaucoup d 'infos pas forcement necessaires sont passées en chemin (ex les metadat entieres sont passées alors qu'on a besoin que de line_count),
#l'optimisation de la modularisation des fonctions.Je decoupe bien en petits morceaux mes taches,mais est ce que je les decoupe bien(au bon endroit) ? etc etc

#Je peux acceder aux infos de deux manieres dans deux cas : 
#J'ai le chemin sensible a la casse -> je peux recuperer l'objet Path correspondant ou l'adresse + les metadata via database["files"][chemin.lower()]
#Et si j'ai le chemin non sensible,je peux recuperer les metadata via database["files"]["chemin"],et  meme creer un objet Path,en recuperant le chemin original via database["files"]["chemin"]["path"]

#Systeme de score plus poussé : réagit au langage du projet.(+ de points pour les fichiers en langage du projet,aucun bonus pour les sites statiques si on a un serveur python par exemple,et depreciation des fichiers d'un autre langage)
#Trouver la stack du projet permet aussi de donner des bonus aux fichiers specifiques au projet( requirements en python,recuperer les headers en c,node-packages,)
#meme pas besoin de se casser la tete on va utiliser un appel LLM pour determiner precisement les presets/langage de la codebase - ou pas