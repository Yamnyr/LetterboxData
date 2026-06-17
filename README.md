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

Le projet suit une architecture **ELT (Extract, Load, Transform)** moderne et cloud-native :

1.  **Ingestion Dynamique (Multi-Threaded Python + TMDB API)** : 
    - Le dashboard inclut un importateur de fichier ZIP directement dans l'interface.
    - Le ZIP est extrait dans un environnement temporaire sécurisé (concurrence multi-utilisateur garantie).
    - L'ingestion interroge l'API TMDB en **parallèle (15 threads concurrents via `ThreadPoolExecutor`)** pour enrichir à la volée les films inconnus du cache, réduisant le temps d'ingestion de **5 minutes à moins de 30 secondes** pour plus de 1 000 films !

2.  **Transformation (dbt compilé "On-the-Fly")** :
    - Pour permettre le déploiement sur Streamlit Cloud sans l'overhead de la CLI d'ingestion ou de dbt, l'application intègre un **compilateur SQL DBT dynamique**.
    - Il lit les modèles SQL situés dans `/dbt_project`, compile les macros dbt (comme `{{ ref() }}` et `{{ source() }}`) et exécute les transformations directement dans la base de données DuckDB de session en tant que Views et Tables.

3.  **Visualisation (Streamlit + Plotly)** :
    - Dashboard interactif haute performance.
    - Design premium respectant la charte graphique de Letterboxd (Dark Mode, accents HSL Orange/Vert/Bleu).

---

## Prérequis

- Python 3.9+
- Une clé API TMDB (gratuite pour un usage personnel).
- Votre archive de données Letterboxd (ZIP obtenu via les paramètres de votre compte > Import & Export > Export Data).

---

## Installation & Lancement Local

1.  **Configuration** :
    Créez un fichier `.env` à la racine :
    ```env
    TMDB_API_KEY=votre_cle_api_ici
    DUCKDB_PATH=letterboxd_data.duckdb
    ```

2.  **Lancement du Dashboard** :
    Vous pouvez lancer directement le dashboard Streamlit :
    ```bash
    pip install -r requirements.txt
    streamlit run app.py
    ```
    *L'application s'ouvrira en **Mode Démo** avec des données pré-existantes. Vous pourrez ensuite téléverser votre propre fichier ZIP dans la barre latérale pour afficher instantanément vos statistiques !*

3.  **Pipeline Classique (Ligne de commande - Optionnel)** :
    Si vous préférez exécuter le pipeline d'ingestion en local via dbt en ligne de commande, placez vos CSV dans un dossier `data/` et lancez :
    ```powershell
    .\run_pipeline.ps1
    ```

---

## Déploiement en Production (Streamlit Cloud)

Cette application est **100% compatible avec Streamlit Community Cloud** grâce à son architecture en mémoire et sa gestion de base de données par session.

1.  Poussez le code sur votre dépôt GitHub (le fichier `.gitignore` a été configuré pour **exclure automatiquement** votre dossier `temp/` et vos fichiers ZIP contenant vos données personnelles).
2.  Créez une application sur [Streamlit Share](https://share.streamlit.com/).
3.  Dans les **Settings** > **Secrets** de votre application Streamlit, ajoutez votre clé TMDB :
    ```toml
    TMDB_API_KEY = "votre_cle_api_tmdb_reelle"
    ```
4.  Enregistrez. L'application est prête à accueillir n'importe quel utilisateur qui pourra y glisser son propre ZIP !

---

## Structure du Projet

```text
├── app.py                 # Application Streamlit (Dashboard principal)
├── scripts/
│   ├── pipeline.py        # Moteur d'extraction, compilation SQL dbt et TMDB multi-threaded
│   └── ingest_tmdb.py     # Script d'ingestion en ligne de commande (ELT local)
├── dbt_project/
│   ├── models/
│   │   ├── staging/       # Nettoyage des données (Models dbt SQL)
│   │   └── marts/         # Tables analytiques finales (Models dbt SQL)
│   └── dbt_project.yml    # Configuration dbt
├── temp/                  # Dossier temporaire pour les zips (Exclu de Git)
└── letterboxd_data.duckdb # Base de données DuckDB locale de démo
```

---

## Note sur le "Score Hipster"
Le score est calculé via une fonction logarithmique sur la popularité moyenne de votre historique. Un score proche de 100 indique que vous privilégiez des films "niche" ou peu connus sur la scène internationale (TMDB), tandis qu'un score plus bas reflète une consommation plus axée sur les blockbusters et les films "mainstream".
