# Letterboxd Data Dashboard Pro

Un dashboard d'analyse cinématographique premium conçu pour sublimer les données de votre export Letterboxd. Cet outil enrichit vos données personnelles avec les métadonnées de **TMDB (The Movie Database)** pour offrir des insights profonds sur vos habitudes de visionnage, vos goûts et votre positionnement par rapport à la communauté mondiale.

![Letterboxd Style](https://img.shields.io/badge/Style-Letterboxd-ff8000?style=for-the-badge&logo=letterboxd)
![Tech Stack](https://img.shields.io/badge/Stack-Python_|_dbt_|_DuckDB_|_Streamlit-00e054?style=for-the-badge)

## Fonctionnalités Clés

- **KPI Dynamiques** : Taux de re-visionnage (via les données du journal), score "Hipster" vs "Mainstream", temps total passé devant des films.
- **Analyses Temporelles** : Analyse par décennies et par année de sortie.
- **Comparaison Communautaire** : Corrélation entre vos notes et les notes mondiales (TMDB).
- **Exploration Géographique** : Carte interactive des pays de production de votre catalogue.
- **Tops & Statistiques** : Classements avancés des réalisateurs et du casting basés sur vos notes moyennes.
- **Recommandations** : Identification des "pépites" dans votre watchlist basées sur les notes communautaires.
- **Habitudes de Visionnage** : Analyse de votre rythme hebdomadaire et de vos jours de prédilection.

## Architecture Technique

Le projet suit une architecture **ELT (Extract, Load, Transform)** moderne et locale :

1.  **Ingestion (Python + TMDB API)** : 
    - Le script `scripts/ingest_tmdb.py` lit vos fichiers CSV Letterboxd (`watched.csv`, `ratings.csv`, etc.).
    - Il identifie les films manquants et récupère les métadonnées via l'API TMDB (Genres, Popularité, Budget, Casting, Pays).
    - Les données brutes (JSON) et les CSV sont chargés dans un entrepôt de données local **DuckDB**.

2.  **Transformation (dbt)** :
    - Utilisation de **dbt (Data Build Tool)** pour structurer la donnée.
    - **Staging** : Nettoyage et typage des données brutes (ex: parsing des dates, extraction des listes JSON).
    - **Marts** : Création de tables agrégées prêtes pour l'analyse (ex: stats par réalisateur, calcul des différences de notes).

3.  **Visualisation (Streamlit + Plotly)** :
    - Dashboard interactif haute performance.
    - Design personnalisé respectant la charte graphique de Letterboxd (Dark Mode, accents Orange/Vert/Bleu).

## Prérequis

- Python 3.9+
- Une clé API TMDB (gratuite pour un usage personnel).
- Votre export Letterboxd (fichiers CSV) placé dans un dossier `data/`.

## Installation & Lancement

1.  **Configuration** :
    Créez un fichier `.env` à la racine :
    ```env
    TMDB_API_KEY=votre_cle_api_ici
    LETTERBOXD_DATA_DIR=data
    DUCKDB_PATH=letterboxd_data.duckdb
    ```

2.  **Pipeline complet** :
    Exécutez le script d'orchestration pour ingérer les données, lancer les transformations dbt et ouvrir le dashboard :
    ```powershell
    .\run_pipeline.ps1
    ```

## Structure du Projet

```text
├── app.py                 # Application Streamlit (Dashboard)
├── scripts/
│   └── ingest_tmdb.py     # Script d'ingestion et enrichissement API
├── dbt_project/
│   ├── models/
│   │   ├── staging/       # Nettoyage des données (Models dbt)
│   │   └── marts/         # Tables analytiques finales
│   └── dbt_project.yml    # Configuration dbt
├── data/                  # Dossier contenant vos CSV Letterboxd
└── letterboxd_data.duckdb # Entrepôt de données local (généré)
```

## Note sur le "Score Hipster"
Le score est calculé via une fonction logarithmique sur la popularité moyenne de votre historique. Un score proche de 100 indique que vous privilégiez des films "niche" ou peu connus sur la scène internationale (TMDB), tandis qu'un score plus bas reflète une consommation plus axée sur les blockbusters et les films "mainstream".
