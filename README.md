# DocumentationAgent v2

DocumentationAgent v2 est un prototype d'agent de generation de documentation pour codebase. Il explore un depot cible, construit une carte des fichiers, interroge un modele LLM pour cadrer le besoin utilisateur, produit un plan, associe les fichiers utiles aux sections, redige chaque section puis exporte la documentation.

Le projet est experimental. Le pipeline complet existe dans le code, mais `app/main.py` est actuellement configure en mode test d'export : l'appel `asyncio.run(main())` est commente et le fichier lance directement un inventaire sur `app/process/little_agent`, puis un export `docx` de 4 sections existantes.

## Workflow

Le workflow complet prevu par `main()` est :

1. Creer un `workflow_id`.
2. Explorer la codebase cible avec `make_inventory(...)`.
3. Conserver une copie pure de l'inventaire.
4. Poser les questions utilisateur.
5. Normaliser les reponses en JSON.
6. Evaluer le README cible.
7. Choisir les fichiers importants.
8. Creer un plan JSON.
9. Adapter les regles de scoring au projet et au plan.
10. Scorer, resumer et associer les fichiers aux sections.
11. Associer l'arborescence aux sections utiles.
12. Rediger les sections Markdown.
13. Exporter en `md`, `docx` ou `odt`.

La review globale des sections generees reste a ajouter.

## Fichiers suivis par Git

Cette documentation couvre les fichiers suivis par Git. Les fichiers locaux, secrets, fixtures, sorties generees et dossiers ignores ne sont pas detailles ici.

| Fichier | Role |
|---|---|
| `.gitignore` | Exclut l'environnement local, les caches, logs, dossier cible `little_agent` et sorties Markdown de `app/process`. |
| `requirements.txt` | Liste les dependances Python : LlamaIndex/Ollama, Langfuse, Pathspec, `pypandoc-binary`, `merm` et `resvg_py`. |
| `app/main.py` | Point d'entree experimental. Contient le pipeline complet, mais lance actuellement un export DOCX de test. |
| `app/model.py` | Configure les clients Ollama, charge l'environnement, instrumente les appels avec Langfuse et fournit `query` / `query_json`. |
| `app/steps.py` | Gere les questions utilisateur, la redaction des sections, l'amelioration/rendu Mermaid et les exports. |
| `app/utils.py` | Contient l'exploration de fichiers, la lecture du `.gitignore`, le scoring, les resumes, les associations fichier/section et la creation du plan. |
| `app/process/reference-doc.docx` | Fichier de reference Pandoc pour l'export `docx`. |
| `app/process/reference-doc.odt` | Fichier de reference Pandoc pour l'export `odt`. |
| `bloc-notes.txt` | Notes de conception sur le workflow cible, le scoring et les futures evolutions. |
| `token_consumption.md` | Estimation de consommation de tokens par etape. |
| `README.md` | Documentation du projet. |

## Architecture

### `app/model.py`

Le module configure deux modeles Ollama via LlamaIndex :

- `first_model`, modele principal utilise pour les appels structurants ;
- `fast_model`, modele secondaire utilise notamment pour l'amelioration des diagrammes et potentiellement la review.

Variables d'environnement utilisees :

- `OLLAMA_MODEL`
- `OLLAMA_BASE_URL`
- `OLLAMA_API_KEY`
- `REVIEW_MODEL`

Les appels sont traces avec Langfuse via `openinference-instrumentation-llama-index`.

Fonctions principales :

- `clean_json_response(content)` nettoie les fences Markdown et extrait un objet JSON quand il existe.
- `query(msg, llm, workflow_run_id, tag)` execute un appel chat et le trace dans Langfuse.
- `query_json(msg, llm, workflow_run_id, tag)` appelle `query`, nettoie la reponse et recommence tant que le JSON n'est pas valide.

### `app/steps.py`

Ce module gere les interactions utilisateur, la redaction et les exports.

Fonctions de cadrage :

- `ask_all_questions(...)` pose les questions de taille, niveau de detail, diagrammes, format, public, objectif, exclusions et commentaires.
- `get_json_resume(...)` transforme les reponses libres en JSON normalise.

Fonctions de redaction :

- `write_section(...)` redige une section Markdown a partir du plan, des resumes de fichiers, de l'arborescence si besoin et des preferences utilisateur.
- `write_all_sections(...)` ecrit `partie_1.md`, `partie_2.md`, etc. dans le dossier de process courant.

Fonctions Mermaid :

- `detect_export_mermaid(...)` parcourt les sections Markdown et detecte les blocs ```mermaid.
- `upgrade_and_fix_diagram(...)` demande a `fast_model` de simplifier, corriger et aerer le diagramme.
- `detect_return_mermaid(...)` rend le diagramme ameliore en SVG avec `merm`, convertit le SVG en PNG avec `resvg_py`, puis remplace le bloc Mermaid par une image Markdown.

Fonctions d'export :

- `md_export(...)` concatene les sections en `documentation.md`.
- `convert_to_docx(...)` convertit les sections en `documentation.docx` avec Pypandoc.
- `convert_to_odt(...)` convertit les sections en `documentation.odt` avec Pypandoc.
- `export(...)` choisit l'export selon le format demande.

Les exports `docx` et `odt` appellent la conversion Mermaid avant Pandoc. L'export `md` conserve les sections Markdown telles quelles.

### `app/utils.py`

Ce module contient la logique documentaire principale.

Exploration :

- `make_inventory(repo_root)` change le dossier courant vers la racine cible puis lance l'inventaire.
- `load_gitignore(spec)` lit le `.gitignore` cible et ajoute `.git`, `assets`, `test*` et `*.pdf`.
- `list_files(repo_root)` construit une structure `tree` et un index `files`.

Chaque fichier inventorie contient notamment :

```json
{
  "name": "main.py",
  "path": "app/main.py",
  "type": "file",
  "extension": ".py",
  "size": 320,
  "lines_count": 42,
  "score": null,
  "sections": [],
  "resume": ""
}
```

Planification :

- `readme_usefulness(...)` classe le README cible comme `utile`, `insuffisant`, `inutile` ou `empty`.
- `get_meaningful_list(...)` selectionne 2 a 8 fichiers importants selon l'arborescence et les preferences utilisateur.
- `create_plan(...)` resume les fichiers importants et produit un plan JSON detaille.

Scoring et association :

- `discover_and_adapt_environment(...)` demande au LLM d'adapter les bonus de scoring.
- `score(...)` calcule un score selon le chemin, le nom, la taille et l'extension.
- `resume(...)` produit un resume fidele d'un fichier.
- `associate(...)` associe un fichier resume a une ou plusieurs sections.
- `decide(...)` traite les fichiers au score intermediaire.
- `classify_tree(...)` associe l'arborescence aux sections utiles.
- `classify_all_docs(...)` applique scoring, resumes et associations sur toute la codebase.
- `score_resume_associate(...)` orchestre les modes `resume`, `associate` et `full`.

Seuils actuels :

- `SCORE_SEUIL_HAUT = 70`
- `SCORE_SEUIL_BAS = 40`

### `app/main.py`

Le fichier contient deux usages :

- `main()`, pipeline complet asynchrone, actuellement non lance car `asyncio.run(main())` est commente.
- un bloc de test direct qui appelle `make_inventory(...)`, puis `export(format="docx", section_number=4, workflow_run_id="1234")`.

Le chemin cible est code en dur vers `app/process/little_agent`. Comme `make_inventory(...)` fait un `os.chdir(...)`, tous les chemins relatifs d'export sont ensuite interpretes depuis cette racine cible.

## Installation

Installer les dependances Python :

```powershell
pip install -r requirements.txt
```

Les dependances d'export/rendu sont embarquees autant que possible :

- Pandoc via `pypandoc-binary` ;
- rendu Mermaid via `merm` ;
- conversion SVG vers PNG via `resvg_py`.

L'objectif est d'eviter les dependances systeme comme `rsvg-convert`, Cairo ou une installation Pandoc separee pour l'usage standard.

## Configuration

Creer un fichier `.env` local. Il est ignore par Git.

Variables utilisees directement par le code :

```env
OLLAMA_MODEL=...
OLLAMA_BASE_URL=...
OLLAMA_API_KEY=...
REVIEW_MODEL=...
```

Langfuse peut aussi necessiter ses variables d'environnement habituelles selon la configuration locale.

## Lancement

Mode actuel de `app/main.py` :

```powershell
python app/main.py
```

Ce mode relance l'inventaire de `app/process/little_agent` et exporte un DOCX a partir des sections deja presentes.

Pour lancer le pipeline complet, il faut remettre l'appel suivant en bas de `app/main.py` :

```python
asyncio.run(main())
```

et retirer ou commenter le bloc de test direct.

## Sorties

Le workflow peut produire :

- `partie_1.md`, `partie_2.md`, etc. ;
- des images Mermaid intermediaires en `.svg` et `.png` ;
- `documentation.md` ;
- `documentation.docx` ;
- `documentation.odt`.

Les sections, images et documents finaux generes sont des artefacts locaux. Les fichiers `app/process/reference-doc.docx` et `app/process/reference-doc.odt` sont des templates Pandoc versionnes.

## Exclusions

L'exploration repose sur le `.gitignore` du projet cible. Il faut fournir a `make_inventory(...)` la racine qui contient le `.gitignore` cible, sinon les exclusions peuvent etre fausses.

Exclusions ajoutees par le code :

- `.git`
- `assets`
- `test*`
- `*.pdf`

Le `.gitignore` du projet DocumentationAgent exclut aussi plusieurs artefacts locaux, dont `little_agent` et `app/process/*.md`.

## Consommation de tokens

`token_consumption.md` donne une estimation des couts pour :

- resume des reponses utilisateur ;
- evaluation du README ;
- choix des fichiers importants ;
- resume par fichier ;
- generation du plan.

La consommation augmente avec la taille de l'arborescence, la longueur des fichiers resumes, la longueur des sections generees et les passes d'amelioration Mermaid.

## Etat d'avancement

Deja present :

- questions utilisateur ;
- normalisation JSON des reponses ;
- configuration LLM Ollama ;
- instrumentation Langfuse ;
- inventaire de fichiers avec respect du `.gitignore` ;
- evaluation du README ;
- selection de fichiers importants ;
- adaptation LLM des regles de scoring ;
- scoring heuristique ;
- resume de fichiers ;
- association fichier/section ;
- association de l'arborescence ;
- generation d'un plan JSON ;
- redaction de sections Markdown ;
- detection, amelioration et rendu des diagrammes Mermaid ;
- conversion SVG vers PNG ;
- export `md`, `docx`, `odt`.

A faire :

- parametrer proprement la racine cible au lieu d'un chemin code en dur ;
- remettre un mode d'execution clair entre pipeline complet et export de test ;
- ajouter une review globale des sections generees ;
- reduire les repetitions entre sections ;
- ajouter des tests automatises ;
- durcir la gestion des erreurs LLM, JSON et Mermaid ;
- clarifier les chemins de sortie ;
- ameliorer le scoring avec imports, entrypoints et signaux propres a chaque stack ;
- eventuellement passer certains appels LLM en asynchrone si le fournisseur accepte les requetes paralleles.
