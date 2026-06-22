from pathlib import Path
import pathspec
import os 
import json


"""
Chemin,taille,nombre de lignes,extension + exclusion gitignore + exclusion assets+tests : pdf + dossiers assets/ et dossier tests/ 
"""
async def make_inventory(repo_root : str):
    root = Path(repo_root)



async def load_gitignore(repo_root : Path):
    gitignore = repo_root / ".gitignore"
    if not gitignore.exists() :
        return None
    
    exclusions = gitignore.read_text(
        encoding="utf-8",
        errors="ignore"
    ).splitlines()
    
    return pathspec.PathSpec.from_lines("gitignore",exclusions)

async def is_ignored(path : Path,repo_root : Path,spec :pathspec.PathSpec) -> bool:
    if spec is None : 
        return False 
    
    file = path.relative_to(repo_root).as_posix()
    return spec.match_file(file)
    
async def list_files(repo_root : Path) -> dict:
    spec = load_gitignore(repo_root)
    for file in repo_root.rglob("*"):
        #creer json en verifiant avant assets + tests + gitignore,et en ajoutant les propriétés a la volée (propriétés calculées par des fonctiones utilitaires)