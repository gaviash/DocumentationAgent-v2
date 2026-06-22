from pathlib import Path
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
    
def list_files(repo_root : Path) -> dict | list:
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
    print(os.listdir())
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
            metadata = {
                "name" : filepath.name,
                "type" : "file",
                "extension" : filepath.suffix,
                "size" :  size,
                "lines_count" : count ,
                "score" : None,
                "sections" : [],
                "resume" : ""
            }
            
            healthy_files["files"][relative_path] = metadata
            add_file_to_tree(healthy_files["tree"],filepath,repo_root,metadata)
    return healthy_files



print(json.dumps(make_inventory(r"C:\Users\Gavriel.Myara\Desktop\DocumentationAgentv2\app\process\little_agent"),indent=2,ensure_ascii=False))