# DocumentationAgent v2

DocumentationAgent v2 est un projet d'agent de generation de documentation pour codebase.

L'objectif est de produire une documentation de bonne qualite avec un workflow explicite, en combinant :

- les besoins de l'utilisateur ;
- une exploration filtree du repository ;
- une carte de la codebase ;
- un plan valide par l'utilisateur ;
- des resumes de fichiers pertinents ;
- une phase d'ecriture puis de review.

Le projet est encore en construction.

## Idee generale

Le workflow vise a eviter une generation directe et floue de documentation.

Au lieu de demander au modele de tout ecrire en une seule fois, l'agent decoupe le travail en etapes :

1. Recueillir les besoins utilisateur.
2. Explorer la codebase en respectant les exclusions.
3. Construire une representation JSON des fichiers.
4. Identifier les fichiers les plus importants.
5. Proposer plusieurs approches de plan.
6. Faire choisir une approche par l'utilisateur.
7. Associer les fichiers pertinents aux sections du plan.
8. Rediger chaque section avec le bon contexte.
9. Relire et corriger le document.
10. Exporter le resultat final.

## Workflow prevu

### 1. Questions utilisateur

L'agent commence par recuperer les informations necessaires a la documentation :

- taille souhaitee ;
- niveau de detail ;
- presence ou non d'un diagramme Mermaid ;
- format de sortie ;
- public vise ;
- objectif de la documentation ;
- fichiers ou sections a exclure ;
- commentaires libres.

Ces reponses sont ensuite transformees en JSON simplifie pour etre reutilisees dans les prompts suivants.

### 2. Exploration de la codebase

L'agent parcourt le dossier projet et construit un inventaire des fichiers.

Chaque fichier peut contenir des metadonnees comme :

- nom ;
- extension ;
- taille ;
- nombre de lignes ;
- score d'importance ;
- sections associees ;
- resume.

L'inventaire contient deux vues :

- `files` : acces direct a un fichier par son chemin ;
- `tree` : representation en arborescence de la codebase.

Exemple simplifie :

```json
{
  "tree": {
    "name": ".",
    "type": "directory",
    "children": {}
  },
  "files": {
    "app/main.py": {
      "name": "main.py",
      "type": "file",
      "extension": ".py",
      "size": 320,
      "lines_count": 42,
      "score": null,
      "sections": [],
      "resume": ""
    }
  }
}
```

### 3. README ou resume initial

Si un README utile existe dans le projet analyse, il sert de base au resume initial.

Si le README est absent ou insuffisant, l'agent peut utiliser l'arbre de fichiers pour demander au modele quels fichiers lire en priorite.

Un README est considere insuffisant s'il ne decrit que des details techniques sans expliquer le projet, son usage ou sa structure globale.

### 4. Proposition de plans

Le modele recoit :

- le resume general du projet ;
- le README ou le resume maison ;
- la codebase map ;
- quelques fichiers importants ;
- les besoins utilisateur.

Il propose ensuite plusieurs approches de plan.

L'utilisateur choisit l'approche qu'il prefere, puis l'agent demande au modele un plan JSON detaille.

Format vise :

```json
{
  "Section 1": {
    "nom": "",
    "taille_approximative": "",
    "diagramme": "oui/non",
    "commentaire_contenu": "",
    "fichiers_concernes": []
  }
}
```

### 5. Scoring et association des fichiers

Une fois le plan valide, l'agent analyse les fichiers pour determiner lesquels sont utiles.

L'objectif est de :

- calculer un score d'importance ;
- resumer les fichiers pertinents ;
- associer chaque fichier aux bonnes sections du plan.

Les criteres possibles de scoring incluent :

- bonus pour les entrypoints ;
- bonus pour les fichiers beaucoup importes ;
- bonus selon l'extension ;
- bonus pour les fichiers lies au framework detecte ;
- malus pour les tres gros fichiers ;
- malus pour les lockfiles ;
- malus pour les tests ;
- malus pour les assets ou fichiers generes.

### 6. Ecriture et review

Chaque section est ecrite avec :

- le plan de la section ;
- les demandes utilisateur ;
- les resumes des fichiers concernes ;
- les consignes de style et de niveau de detail.

Une phase de review doit ensuite verifier :

- la coherence globale ;
- les oublis ;
- les repetitions ;
- la clarte ;
- les sections faibles.

## Exclusions

L'exploration doit respecter le `.gitignore` du projet analyse.

Point important : l'utilisateur doit fournir comme racine le dossier qui contient le `.gitignore`.

Sinon, les exclusions peuvent ne pas etre detectees correctement.

Des exclusions supplementaires sont prevues :

- `.git` ;
- `assets` ;
- `test*` ;
- `*.pdf`.

## Etat actuel

Le projet contient deja :

- une premiere logique de questions utilisateur dans `app/steps.py` ;
- des appels modele dans `app/model.py` ;
- une exploration de fichiers dans `app/utils.py` ;
- un cas de test dans `app/process/little_agent`.

Le systeme de scoring, l'association automatique fichiers/sections, la redaction complete et l'export final sont encore a developper.

## Installation

Installer les dependances :

```powershell
pip install -r requirements.txt
```

## Lancement

Exemple :

```powershell
python app/main.py
```

Pour tester l'inventaire de fichiers :

```powershell
python app/utils.py
```
