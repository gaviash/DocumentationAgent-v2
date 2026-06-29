# DocumentationAgent v2

DocumentationAgent v2 est un prototype d'agent de generation de documentation pour une codebase. Il explore un depot, construit une carte de fichiers, interroge un modele LLM pour comprendre les besoins utilisateur, puis prepare un plan de documentation base sur les fichiers juges pertinents.

Le projet est encore en construction : l'exploration, le resume, le scoring, l'association fichier/section et la generation d'un plan existent deja en partie, mais l'ecriture finale de la documentation, la review et l'export ne sont pas encore implementes.

## Principe

L'objectif est d'eviter une generation directe et floue de documentation. Le workflow est decoupe en etapes explicites :

1. Interroger l'utilisateur sur la documentation attendue.
2. Transformer les reponses en JSON exploitable.
3. Explorer la codebase en respectant le `.gitignore` du projet cible.
4. Construire une carte de fichiers avec metadonnees.
5. Evaluer si le README du projet cible est utile.
6. Choisir quelques fichiers importants pour comprendre le projet.
7. Resumer ces fichiers avec un LLM.
8. Generer un plan de documentation en JSON.
9. Scorer, resumer et associer les fichiers aux sections du plan.

Les etapes d'ecriture section par section, de review et d'export sont decrites dans les notes du projet, mais restent a developper.

## Fichiers suivis par Git

Cette documentation ne couvre que les fichiers suivis par Git. Les dossiers et fichiers ignores ou non suivis, comme `.env`, `.venv`, `docsgen`, `logs.log`, `prompts/` ou `bloc-notes.md`, ne sont pas documentes ici.

| Fichier | Role |
|---|---|
| `.gitignore` | Definit les fichiers locaux a exclure du depot : environnement virtuel, cache, logs, donnees de process, documentation generee, etc. |
| `requirements.txt` | Liste les dependances Python du prototype. |
| `app/main.py` | Point d'entree experimental du workflow. Cree un `workflow_id`, lance l'inventaire, interroge l'utilisateur, analyse le README, choisit les fichiers utiles, cree le plan et lance une association partielle des documents. |
| `app/model.py` | Configure les modeles Ollama via LlamaIndex, charge les variables d'environnement, instrumente les appels avec Langfuse et fournit `query` / `query_json`. |
| `app/steps.py` | Contient les questions posees a l'utilisateur et la transformation des reponses libres en JSON resume. |
| `app/utils.py` | Regroupe l'exploration de fichiers, la lecture du `.gitignore`, le scoring, le resume de fichiers, l'association aux sections et la creation du plan. |
| `bloc-notes.txt` | Notes de conception sur le workflow cible, les arbitrages de planification, le scoring, l'association des fichiers et la future generation. |
| `token_consumption.md` | Estimation de consommation de tokens par etape du workflow. |
| `README.md` | Documentation du projet. |

## Architecture actuelle

### `app/model.py`

Le module modele configure deux clients Ollama :

- `first_model`, utilise pour la plupart des appels structurants ;
- `fast_model`, prevu pour des appels plus rapides ou de review.

Les variables d'environnement attendues sont chargees avec `python-dotenv` :

- `OLLAMA_MODEL`
- `OLLAMA_BASE_URL`
- `OLLAMA_API_KEY`
- `REVIEW_MODEL`

Les appels LLM sont traces avec Langfuse via `openinference-instrumentation-llama-index`.

Fonctions principales :

- `clean_json_response(content)` nettoie une reponse LLM entouree de fences Markdown ou de texte parasite pour en extraire un objet JSON.
- `query(msg, llm, workflow_run_id, tag)` execute un appel chat et l'enregistre dans Langfuse.
- `query_json(msg, llm, workflow_run_id, tag)` appelle `query`, nettoie la reponse et recommence tant que le JSON n'est pas valide.

### `app/steps.py`

Ce module gere l'etape de cadrage utilisateur.

`ask_all_questions(ask_func)` pose huit questions :

- taille souhaitee ;
- niveau de detail ;
- presence d'un diagramme Mermaid ;
- format de sortie ;
- public vise ;
- objectif ;
- fichiers ou sections a exclure ;
- commentaires libres.

`get_json_resume(...)` envoie les reponses au modele pour produire un dictionnaire normalise contenant notamment `taille`, `niveau de detail`, `diagramme`, `format`, `public vise`, `objectif`, `Exclusion` et `commentaires`.

### `app/utils.py`

Ce module contient la majorite de la logique du prototype.

Exploration :

- `make_inventory(repo_root)` change le dossier courant vers la racine cible, puis lance l'inventaire.
- `load_gitignore(spec)` lit le `.gitignore` de la racine cible et ajoute aussi des exclusions fixes : `assets`, `*.pdf`, `test*`, `.git`.
- `list_files(repo_root)` construit une structure JSON avec deux vues :
  - `tree`, une arborescence imbriquee ;
  - `files`, un dictionnaire indexe par chemin relatif en minuscules.

Chaque fichier inventorie contient :

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

Analyse et planification :

- `readme_usefulness(...)` classe le README cible comme `utile`, `insuffisant`, `inutile` ou `empty`.
- `get_meaningful_list(...)` demande au LLM une liste de 2 a 8 fichiers importants, a partir de l'arborescence.
- `create_plan(...)` resume les fichiers importants, injecte les preferences utilisateur et produit un plan JSON.

Scoring et association :

- `score(...)` calcule un score heuristique selon le chemin, le nom du fichier, l'extension et le nombre de lignes.
- `resume(...)` demande au LLM un resume dense et fidele d'un fichier.
- `associate(...)` associe un fichier resume a une ou plusieurs sections du plan.
- `decide(...)` traite les fichiers au score intermediaire en demandant au LLM s'ils sont utiles.
- `score_resume_associate(...)` orchestre ces comportements selon un mode : `resume`, `associate` ou `full`.

Les seuils actuels sont :

- `SCORE_SEUIL_HAUT = 70`
- `SCORE_SEUIL_BAS = 40`

### `app/main.py`

`main.py` assemble les briques du workflow :

1. generation d'un `workflow_id` ;
2. inventaire d'une codebase cible ;
3. questions utilisateur ;
4. evaluation du README ;
5. selection des fichiers utiles ;
6. creation du plan ;
7. association de certains fichiers aux sections.

Le fichier est encore experimental. La racine analysee est actuellement codee en dur dans `main.py` et doit etre adaptee avant usage sur une autre codebase.

## Installation

Creer un environnement Python, puis installer les dependances :

```powershell
pip install -r requirements.txt
```

## Configuration

Creer un fichier `.env` local avec les variables necessaires aux appels Ollama et Langfuse. Ce fichier est ignore par Git.

Variables utilisees directement par le code :

```env
OLLAMA_MODEL=...
OLLAMA_BASE_URL=...
OLLAMA_API_KEY=...
REVIEW_MODEL=...
```

Langfuse peut aussi necessiter ses variables d'environnement habituelles selon la configuration locale.

## Lancement

Point d'entree principal :

```powershell
python app/main.py
```

Attention : avant de lancer ce script, modifier dans `app/main.py` le chemin passe a `make_inventory(...)` pour pointer vers la codebase a documenter.

Pour tester l'inventaire depuis le module utilitaire :

```powershell
python app/utils.py
```

Le module `utils.py` ne contient toutefois pas de bloc `if __name__ == "__main__"` dedie ; cette commande ne produit donc pas de test complet dans l'etat actuel.

## Exclusions

L'exploration repose sur le `.gitignore` du projet cible. Il faut donc fournir a `make_inventory(...)` la racine du dossier qui contient ce `.gitignore`.

Si la racine fournie n'est pas la bonne, les exclusions peuvent etre incompletes ou incorrectes.

Exclusions ajoutees par le code en plus du `.gitignore` :

- `.git`
- `assets`
- `test*`
- `*.pdf`

## Consommation de tokens

`token_consumption.md` donne une estimation des couts par etape :

- resume des reponses utilisateur ;
- evaluation du README ;
- choix des fichiers importants ;
- resume par fichier ;
- generation du plan.

La consommation depend surtout de la taille de l'arborescence, du README et du nombre de fichiers resumes.

## Etat d'avancement

Deja present :

- questions utilisateur ;
- normalisation JSON des reponses ;
- configuration LLM Ollama ;
- instrumentation Langfuse ;
- inventaire de fichiers avec respect du `.gitignore` ;
- evaluation du README ;
- selection de fichiers importants ;
- scoring heuristique ;
- resume de fichiers ;
- association fichier/section ;
- generation d'un plan JSON.

A faire :

- finaliser l'association de tous les fichiers au plan ;
- implementer la redaction des sections ;
- implementer la review globale ;
- exporter le document final (`md`, `txt`, `docx`, `odt`) ;
- ajouter des tests automatises ;
- ameliorer le scoring avec une detection de stack, d'imports et d'entrees applicatives ;
- eventuellement passer les appels LLM en asynchrone si le fournisseur utilise accepte les requetes paralleles.
