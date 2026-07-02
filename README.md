# DocumentationAgent v2

DocumentationAgent v2 est un prototype d'agent de generation de documentation pour codebase. Il explore un depot cible, construit une carte des fichiers, interroge un modele LLM pour cadrer le besoin utilisateur, produit un plan, associe les fichiers utiles aux sections, redige chaque section puis exporte la documentation.

Le projet reste experimental, mais le flux principal va maintenant plus loin qu'un simple plan : il peut generer des fichiers Markdown de section et produire une sortie finale en `md`, `docx` ou `odt`.

## Workflow

Le workflow vise a eviter une generation directe et floue. Il decoupe la documentation en etapes :

1. Interroger l'utilisateur sur la documentation attendue.
2. Transformer les reponses en JSON exploitable.
3. Explorer la codebase cible en respectant son `.gitignore`.
4. Construire une carte de fichiers avec metadonnees.
5. Evaluer si le README cible est utile, insuffisant ou inutilisable.
6. Selectionner les fichiers importants pour comprendre le projet.
7. Resumer ces fichiers avec un LLM.
8. Generer un plan JSON de documentation.
9. Adapter les regles de scoring au projet et au plan.
10. Scorer, resumer et associer les fichiers aux sections.
11. Associer l'arborescence aux sections qui en ont besoin.
12. Rediger chaque section en Markdown.
13. Exporter la documentation finale.

La review globale reste a ajouter.

## Fichiers suivis par Git

Cette documentation couvre les fichiers suivis par Git. Les fichiers locaux, secrets, fixtures de test, generations et dossiers ignores ne sont pas detailles ici.

| Fichier | Role |
|---|---|
| `.gitignore` | Exclut l'environnement local, les caches, logs, dossiers de generation et sorties Markdown de `app/process`. |
| `requirements.txt` | Liste les dependances Python du prototype, dont LlamaIndex/Ollama, Langfuse, Pathspec et Pypandoc. |
| `app/main.py` | Point d'entree experimental qui orchestre le workflow complet : inventaire, questions, README, plan, scoring, association, redaction et export. |
| `app/model.py` | Configure les clients Ollama, charge l'environnement, instrumente les appels avec Langfuse et fournit `query` / `query_json`. |
| `app/steps.py` | Gere les questions utilisateur, la redaction des sections et les exports `md`, `docx`, `odt`. |
| `app/utils.py` | Contient l'exploration de fichiers, la lecture du `.gitignore`, le scoring, les resumes, les associations fichier/section et la creation du plan. |
| `app/process/reference-doc.docx` | Fichier de reference Pandoc utilise comme modele de styles pour l'export `docx`. |
| `app/process/reference-doc.odt` | Fichier de reference Pandoc utilise comme modele de styles pour l'export `odt`. |
| `bloc-notes.txt` | Notes de conception sur le workflow cible, les arbitrages de scoring et les futures evolutions. |
| `token_consumption.md` | Estimation de consommation de tokens par etape. |
| `README.md` | Documentation du projet. |

## Architecture

### `app/model.py`

Le module configure deux modeles Ollama via LlamaIndex :

- `first_model`, modele principal utilise pour les appels structurants ;
- `fast_model`, modele prevu pour des appels rapides ou de review.

Variables d'environnement utilisees :

- `OLLAMA_MODEL`
- `OLLAMA_BASE_URL`
- `OLLAMA_API_KEY`
- `REVIEW_MODEL`

Les appels sont traces avec Langfuse via `openinference-instrumentation-llama-index`.

Fonctions principales :

- `clean_json_response(content)` extrait un objet JSON depuis une reponse LLM eventuellement entouree de fences Markdown.
- `query(msg, llm, workflow_run_id, tag)` execute un appel chat et le trace dans Langfuse.
- `query_json(msg, llm, workflow_run_id, tag)` appelle `query`, nettoie la reponse et recommence tant que le JSON n'est pas valide.

### `app/steps.py`

Ce module gere les interactions de haut niveau avec l'utilisateur et la production finale.

`ask_all_questions(ask_func)` pose les questions de cadrage :

- taille de la documentation ;
- niveau de detail ;
- presence d'un diagramme Mermaid ;
- format de sortie ;
- public vise ;
- objectif ;
- exclusions ;
- commentaires libres.

`get_json_resume(...)` transforme ces reponses en JSON normalise.

`write_section(...)` redige une section Markdown a partir :

- du plan de section ;
- des resumes de fichiers associes ;
- de l'arborescence si elle est utile a cette section ;
- des preferences utilisateur conservees.

`write_all_sections(...)` ecrit les fichiers `partie_1.md`, `partie_2.md`, etc. dans le dossier de process courant.

Fonctions d'export :

- `md_export(...)` concatene les sections en `documentation.md` ;
- `convert_to_docx(...)` convertit les sections en `documentation.docx` avec Pypandoc ;
- `convert_to_odt(...)` convertit les sections en `documentation.odt` avec Pypandoc ;
- `export(...)` choisit l'export selon le format demande.

Pour `docx` et `odt`, Pandoc doit etre disponible sur la machine. Les exports utilisent les fichiers de reference versionnes dans `app/process` :

- `app/process/reference-doc.docx`
- `app/process/reference-doc.odt`

### `app/utils.py`

Ce module contient la majeure partie de la logique documentaire.

Exploration :

- `make_inventory(repo_root)` place le processus dans la racine cible puis lance l'inventaire.
- `load_gitignore(spec)` lit le `.gitignore` cible et ajoute des exclusions fixes : `assets`, `*.pdf`, `test*`, `.git`.
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
- `get_meaningful_list(...)` selectionne 2 a 8 fichiers utiles en tenant compte de l'arborescence et des preferences utilisateur.
- `create_plan(...)` resume les fichiers importants et produit un plan JSON detaille.

Scoring et association :

- `discover_and_adapt_environment(...)` demande au LLM d'adapter les bonus de scoring au projet et au plan.
- `score(...)` calcule un score heuristique avec bonus de chemin, nom, extension et taille.
- `resume(...)` produit un resume dense et fidele d'un fichier.
- `associate(...)` associe un fichier resume a une ou plusieurs sections.
- `decide(...)` traite les fichiers au score intermediaire en lisant leur contenu.
- `classify_tree(...)` associe l'arborescence aux sections qui en ont besoin.
- `classify_all_docs(...)` applique le scoring, les resumes et les associations sur toute la codebase.
- `score_resume_associate(...)` orchestre ces comportements selon le mode `resume`, `associate` ou `full`.

Seuils actuels :

- `SCORE_SEUIL_HAUT = 70`
- `SCORE_SEUIL_BAS = 40`

### `app/main.py`

`main.py` assemble le pipeline :

1. cree un `workflow_id` ;
2. construit l'inventaire de la codebase cible ;
3. conserve une copie pure de l'inventaire ;
4. interroge l'utilisateur ;
5. evalue le README ;
6. selectionne les fichiers importants ;
7. cree le plan ;
8. adapte les regles de scoring ;
9. classe et associe tous les documents ;
10. redige toutes les sections ;
11. exporte le resultat final.

La racine cible est encore codee en dur dans `main.py`. Elle doit etre modifiee avant usage sur un autre projet.

## Installation

Installer les dependances Python :

```powershell
pip install -r requirements.txt
```

Pour les exports `docx` et `odt`, installer aussi Pandoc si la distribution locale de Pypandoc ne le fournit pas.

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

Point d'entree principal :

```powershell
python app/main.py
```

Avant lancement, adapter dans `app/main.py` le chemin passe a `make_inventory(...)`. Il doit pointer vers la racine du projet a documenter, idealement le dossier qui contient le `.gitignore` de ce projet.

## Sorties

Le workflow ecrit les sections sous forme de fichiers Markdown `partie_1.md`, `partie_2.md`, etc., puis produit une documentation finale selon le format demande :

- `documentation.md`
- `documentation.docx`
- `documentation.odt`

Les sections et documents finaux generes sont consideres comme des artefacts locaux et ne sont pas versionnes. Les fichiers `app/process/reference-doc.docx` et `app/process/reference-doc.odt`, eux, sont des templates Pandoc versionnes.

## Exclusions

L'exploration repose sur le `.gitignore` du projet cible. Si la racine fournie ne contient pas le bon `.gitignore`, les exclusions peuvent etre fausses.

Exclusions ajoutees par le code :

- `.git`
- `assets`
- `test*`
- `*.pdf`

Le `.gitignore` du projet DocumentationAgent exclut aussi les sorties locales et de process, notamment `app/process/*.md`. Les fichiers de reference Pandoc de `app/process` ne sont pas ignores.

## Consommation de tokens

`token_consumption.md` donne une estimation des couts par etape :

- resume des reponses utilisateur ;
- evaluation du README ;
- choix des fichiers importants ;
- resume par fichier ;
- generation du plan.

La consommation depend surtout de la taille de l'arborescence, du README, du nombre de fichiers resumes et de la longueur des sections generees.

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
- export `md`, `docx`, `odt`.

A faire :

- parametrer proprement la racine cible au lieu d'un chemin code en dur ;
- ajouter une review globale des sections generees ;
- reduire les repetitions entre sections ;
- ajouter des tests automatises ;
- durcir la gestion des erreurs JSON et des reponses LLM invalides ;
- clarifier les chemins de sortie ;
- ameliorer le scoring avec des imports, entrypoints et signaux propres a chaque stack ;
- eventuellement passer certains appels LLM en asynchrone si le fournisseur accepte les requetes paralleles.
