import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import os
from dotenv import load_dotenv
import math
import tempfile
import shutil
from scripts.pipeline import unzip_and_locate_csvs, run_dynamic_pipeline, load_all_dataframes_from_db

load_dotenv()

DB_PATH = os.getenv("DUCKDB_PATH", "letterboxd_data.duckdb")

st.set_page_config(
    page_title="Letterboxd Stats Pro",
    page_icon="🎬",
    layout="wide",
)

# Custom CSS for Letterboxd premium look
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background-color: #14181c;
        color: #9ab;
    }
    
    /* Metrics / Cards */
    [data-testid="stMetric"] {
        background-color: #2c3440;
        padding: 20px;
        border-radius: 4px;
        border-bottom: 3px solid #456;
        transition: transform 0.2s;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-bottom-color: #ff8000;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #ffffff !important;
        font-family: 'Graphik', sans-serif;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Dividers */
    hr {
        border-top: 1px solid #456;
        margin: 2em 0;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #1c232b;
        border-right: 1px solid #456;
    }
    
    /* Interactive Elements */
    .stButton>button {
        background-color: #00e054;
        color: white;
        font-weight: bold;
        border: none;
        border-radius: 3px;
    }
    .stButton>button:hover {
        background-color: #00b344;
        color: white;
    }
    
    /* Dataframes */
    .stDataFrame {
        background-color: #1c232b;
        border-radius: 4px;
        border: 1px solid #456;
    }
    
    /* Metric Labels */
    [data-testid="stMetricLabel"] {
        color: #9ab !important;
        text-transform: uppercase;
        font-size: 0.8em;
        letter-spacing: 0.1em;
    }
    
    /* Metric Values */
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Session State Initialization
if "dataframes" not in st.session_state:
    st.session_state.dataframes = None
if "is_uploaded" not in st.session_state:
    st.session_state.is_uploaded = False
if "username" not in st.session_state:
    st.session_state.username = "Démo"
if "last_uploaded_file" not in st.session_state:
    st.session_state.last_uploaded_file = None



# Try loading default DB if no user database uploaded yet
if st.session_state.dataframes is None:
    if os.path.exists(DB_PATH):
        try:
            st.session_state.dataframes = load_all_dataframes_from_db(DB_PATH)
            st.session_state.is_uploaded = False
            st.session_state.username = "Démo"
        except Exception as e:
            st.error(f"Impossible de charger la base de données par défaut : {e}")
            st.stop()

# Sidebar: Data Import section
st.sidebar.markdown("---")
st.sidebar.subheader("📤 Importer vos données")
st.sidebar.markdown(
    "Visualisez vos propres statistiques Letterboxd !\n"
    "1. Allez dans vos paramètres Letterboxd.\n"
    "2. Cliquez sur **Import & Export** puis **Export Data**.\n"
    "3. Glissez-déposez le ZIP ci-dessous !"
)

# API Key config
api_key_env = os.getenv("TMDB_API_KEY", "")
tmdb_api_key = st.sidebar.text_input(
    "Clé API TMDB (Optionnel)",
    type="password",
    value=api_key_env,
    help="Utilisée pour enrichir vos nouveaux films avec genres, réalisateurs, etc. Si vide, l'application n'enrichira pas vos nouveaux films."
)

uploaded_file = st.sidebar.file_uploader(
    "Sélectionnez votre ZIP Letterboxd",
    type=["zip"],
    help="Fichier ZIP exporté depuis Letterboxd"
)

# Dynamic pipeline execution on file upload
if uploaded_file is not None:
    if st.session_state.last_uploaded_file != uploaded_file.name:
        with st.status("🚀 Traitement de votre archive Letterboxd...", expanded=True) as status:
            try:
                # Step 1: ZIP extraction
                status.write("📂 Étape 1/3 : Extraction du fichier ZIP...")
                temp_dir = tempfile.TemporaryDirectory()
                csv_dir = unzip_and_locate_csvs(uploaded_file, temp_dir.name)
                
                # Try to extract username
                folder_name = os.path.basename(csv_dir)
                username = "Utilisateur"
                if folder_name.startswith("letterboxd-"):
                    parts = folder_name.split("-")
                    if len(parts) > 1:
                        username = parts[1]
                
                # Step 2: Database preparation
                status.write("💾 Étape 2/3 : Préparation de la base de données...")
                session_db_path = os.path.join(temp_dir.name, "letterboxd_session.duckdb")
                if os.path.exists(DB_PATH):
                    shutil.copy(DB_PATH, session_db_path)
                
                # Step 3: Run pipeline with progress callback
                status.write("🔍 Étape 3/3 : Récupération des films manquants depuis TMDB...")
                progress_bar = st.progress(0.0)
                
                def progress_cb(current, total, message):
                    if total > 0:
                        progress_bar.progress(current / total)
                        status.write(f"🎬 Ingestion TMDB : {message} ({current}/{total})")
                    else:
                        status.write(message)
                
                run_dynamic_pipeline(
                    csv_dir=csv_dir,
                    db_path=session_db_path,
                    dbt_project_dir="dbt_project",
                    tmdb_api_key=tmdb_api_key,
                    progress_callback=progress_cb
                )
                
                # Load all dataframes in session
                status.write("📊 Finalisation du chargement des graphiques...")
                st.session_state.dataframes = load_all_dataframes_from_db(session_db_path)
                st.session_state.is_uploaded = True
                st.session_state.username = username
                st.session_state.last_uploaded_file = uploaded_file.name
                
                # Clean up temp folder
                try:
                    temp_dir.cleanup()
                except:
                    pass
                
                status.update(label="✅ Données chargées avec succès !", state="complete", expanded=False)
                st.toast("🎉 Vos données Letterboxd ont été chargées avec succès !")
                st.rerun()
                
            except Exception as e:
                status.update(label="❌ Erreur lors de l'analyse des données", state="error", expanded=True)
                st.error(f"Une erreur est survenue : {e}")

# If we have uploaded data, show a button to reset and go back to Demo Mode
if st.session_state.is_uploaded:
    if st.sidebar.button("🔙 Retourner au profil de Démo", key="reset_demo_btn"):
        st.session_state.dataframes = None
        st.session_state.is_uploaded = False
        st.session_state.username = "Démo"
        st.session_state.last_uploaded_file = None
        st.rerun()

# Welcome screen if no data is loaded at all
if st.session_state.dataframes is None:
    st.title("🎬 Letterboxd Personal Data Pipeline")
    st.markdown("### Votre univers cinématographique, visualisé")
    st.info("👋 Bienvenue ! Veuillez téléverser votre fichier ZIP Letterboxd dans la barre latérale pour commencer.")
    st.stop()

# Unpack dataframes for UI
dfs = st.session_state.dataframes
df_movies = dfs["mart_movies"]
df_watched = dfs["stg_watched"]
df_ratings = dfs["stg_ratings"]
df_genres = dfs["mart_movie_genres"]
df_countries = dfs["mart_movie_countries"]
df_crew = dfs["mart_movie_crew"]
df_cast = dfs["mart_movie_cast"]
df_diary = dfs["stg_diary"]

# Premium Dynamic Title
if st.session_state.is_uploaded:
    st.title(f"🎬 Statistiques Letterboxd de @{st.session_state.username}")
    st.markdown("### Votre univers cinématographique, visualisé")
else:
    st.title("🎬 Letterboxd Personal Data Pipeline")
    st.markdown("### Profil de Démo — Visualisez votre univers cinématographique")

# Barre latérale - Filtres
st.sidebar.title("🔍 Filtres")
unique_years = []
if not df_watched.empty:
    unique_years = sorted([int(y) for y in df_watched['watch_date'].dt.year.dropna().unique()], reverse=True)

selected_year = st.sidebar.selectbox("Sélectionner l'année", ["Toutes"] + [str(y) for y in unique_years])

# Filter data based on year
if selected_year != "Toutes":
    year_int = int(selected_year)
    df_watched_filtered = df_watched[df_watched['watch_date'].dt.year == year_int]
    df_ratings_filtered = df_ratings[df_ratings['rating_date'].dt.year == year_int]
    df_diary_filtered = df_diary[df_diary['diary_date'].dt.year == year_int]
else:
    df_watched_filtered = df_watched
    df_ratings_filtered = df_ratings
    df_diary_filtered = df_diary

# IMPORTANT: Ensure all movie-based charts only show movies actually WATCHED
# This avoids including the watchlist in Genres, Languages, etc.
df_movies_filtered = df_movies.merge(df_watched_filtered[['movie_title', 'release_year']], on=['movie_title', 'release_year'], how='inner')
df_genres_filtered = df_genres.merge(df_watched_filtered[['movie_title', 'release_year']], on=['movie_title', 'release_year'], how='inner')
df_countries_filtered = df_countries.merge(df_watched_filtered[['movie_title', 'release_year']], on=['movie_title', 'release_year'], how='inner')

# Charger les Likes
try:
    df_likes = dfs.get("stg_likes", pd.DataFrame())
    if selected_year != "Toutes":
        df_likes_filtered = df_likes[df_likes['like_date'].dt.year == int(selected_year)]
    else:
        df_likes_filtered = df_likes
except:
    df_likes_filtered = pd.DataFrame()

# --- CHIFFRES CLÉS (KPIs) ---
rewatch_rate = 0
if not df_diary_filtered.empty:
    rewatch_rate = (df_diary_filtered['is_rewatch'].sum() / len(df_diary_filtered)) * 100

hipster_score = 0
if not df_movies_filtered.empty:
    avg_pop = df_movies_filtered['tmdb_popularity'].mean()
    # Score basé sur log10 de la popularité (plus c'est bas, plus c'est hipster)
    pop_idx = min(1.0, (math.log10(avg_pop + 1) / 2.0)) if avg_pop > 0 else 0
    hipster_score = (1 - pop_idx) * 100

col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("Vus", len(df_watched_filtered))
with col2:
    st.metric("Likes", len(df_likes_filtered))
with col3:
    avg_r = df_ratings_filtered['rating_value'].mean() if not df_ratings_filtered.empty else 0
    st.metric("Note Moyenne", f"{avg_r:.2f}")
with col4:
    st.metric("Re-visionnage", f"{rewatch_rate:.1f}%")
with col5:
    st.metric("Score Hipster", f"{hipster_score:.1f}/100")
with col6:
    total_min = df_movies_filtered['runtime_minutes'].sum()
    if total_min > 1440:
        st.metric("Temps passé", f"{total_min/1440:.1f} j")
    else:
        st.metric("Temps passé", f"{total_min/60:.1f} h")

# --- ANALYSE DE L'ACTIVITÉ ---
col_act, col_heat = st.columns([2, 1])

with col_act:
    st.subheader("� RYTHME DE VISIONNAGE")
    if not df_watched_filtered.empty:
        df_watched_filtered['week'] = df_watched_filtered['watch_date'].dt.to_period('W').apply(lambda r: r.start_time)
        week_counts = df_watched_filtered.groupby('week').size().reset_index(name='Nombre de films')
        fig_activity = px.bar(week_counts, x='week', y='Nombre de films', 
                             template="plotly_dark", color_discrete_sequence=['#00e054']) # Vert Letterboxd
        fig_activity.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_activity, use_container_width=True)

with col_heat:
    st.subheader("� JOURS DE PRÉDILECTION")
    if not df_watched_filtered.empty:
        df_watched_filtered['day_of_week'] = df_watched_filtered['watch_date'].dt.day_name()
        days_fr = {'Monday': 'Lun', 'Tuesday': 'Mar', 'Wednesday': 'Mer', 'Thursday': 'Jeu', 'Friday': 'Ven', 'Saturday': 'Sam', 'Sunday': 'Dim'}
        df_watched_filtered['jour_fr'] = df_watched_filtered['day_of_week'].map(days_fr)
        days_order = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
        day_stats = df_watched_filtered['jour_fr'].value_counts().reindex(days_order).fillna(0).reset_index()
        day_stats.columns = ['Jour', 'Films']
        fig_days = px.bar(day_stats, x='Jour', y='Films', 
                          template="plotly_dark", color='Films', color_continuous_scale=['#2c3440', '#00e054'])
        fig_days.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False)
        st.plotly_chart(fig_days, use_container_width=True)

# --- ANALYSE TEMPORELLE ---
st.divider()
col_dec, col_release = st.columns(2)

with col_dec:
    st.subheader("🕰️ VOL DANS LE TEMPS (DÉCENNIES)")
    df_movies_filtered['decade'] = (df_movies_filtered['release_year'] // 10) * 10
    decade_stats = df_movies_filtered.groupby('decade').agg({'movie_title': 'count', 'user_avg_rating': 'mean'}).reset_index()
    decade_stats['decade_str'] = decade_stats['decade'].astype(str) + "s"
    fig_decades = px.bar(decade_stats, x='decade_str', y='movie_title', color='user_avg_rating', 
                         template="plotly_dark", color_continuous_scale=['#14181c', '#40bcf4'],
                         labels={'movie_title': 'Films', 'decade_str': 'Décennie', 'user_avg_rating': 'Note'})
    fig_decades.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False)
    st.plotly_chart(fig_decades, use_container_width=True)

with col_release:
    st.subheader("📅 FILMS PAR ANNÉE DE SORTIE")
    release_year_counts = df_movies_filtered['release_year'].value_counts().reset_index().sort_values('release_year')
    fig_release = px.area(release_year_counts, x='release_year', y='count', 
                          template="plotly_dark", color_discrete_sequence=['#ff8000']) # Orange Letterboxd
    fig_release.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_release, use_container_width=True)

# --- TOI VS LA COMMUNAUTÉ ---
st.divider()
col_comm, col_pop = st.columns(2)

with col_comm:
    st.subheader("⚖️ TOI VS LA COMMUNAUTÉ")
    df_movies_filtered['user_rating_scaled'] = df_movies_filtered['user_avg_rating'] * 2
    fig_comp = px.scatter(df_movies_filtered, x='tmdb_vote_average', y='user_rating_scaled', 
                          hover_name='movie_title', template="plotly_dark",
                          labels={'tmdb_vote_average': 'Note Mondiale', 'user_rating_scaled': 'Ta Note'},
                          color='user_rating_scaled', color_continuous_scale=['#ff8000', '#00e054'])
    fig_comp.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False)
    st.plotly_chart(fig_comp, use_container_width=True)

with col_pop:
    st.subheader("🍿 INDICE DE FOULE ('HIPSTER')")
    fig_pop = px.scatter(df_movies_filtered, x='tmdb_popularity', y='user_avg_rating', 
                         hover_name='movie_title', template="plotly_dark",
                         labels={'tmdb_popularity': 'Popularité', 'user_avg_rating': 'Note'},
                         size='tmdb_popularity', color='user_avg_rating', color_continuous_scale=['#40bcf4', '#ff8000'])
    fig_pop.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False)
    st.plotly_chart(fig_pop, use_container_width=True)

# --- DURÉE DES FILMS ---
st.divider()
st.subheader("⏳ RÉPARTITION DES DURÉES")
if not df_movies_filtered.empty:
    fig_runtime = px.histogram(df_movies_filtered, x='runtime_minutes', nbins=30, 
                               template="plotly_dark", color_discrete_sequence=['#40bcf4'],
                               labels={'runtime_minutes': 'Durée (minutes)'})
    avg_runtime = df_movies_filtered['runtime_minutes'].mean()
    fig_runtime.add_vline(x=avg_runtime, line_dash="dash", line_color="#ff8000", 
                         annotation_text=f"Moyenne: {avg_runtime:.0f} min", annotation_font_color="#ff8000")
    fig_runtime.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_runtime, use_container_width=True)

# --- GENRES & LANGUES ---
st.divider()
col_gen, col_lang, col_oc = st.columns(3)

with col_gen:
    st.subheader("🌋 GENRES TOP 10")
    genre_counts = df_genres_filtered['genre_name'].value_counts().reset_index()
    fig_genres = px.bar(genre_counts.head(10), x='count', y='genre_name', orientation='h', 
                        template="plotly_dark", color='count', color_continuous_scale=['#2c3440', '#40bcf4'])
    fig_genres.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False, yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_genres, use_container_width=True)

with col_lang:
    st.subheader("🌐 LANGUES TOP 10")
    lang_counts = df_movies_filtered['original_language'].value_counts().reset_index()
    fig_lang = px.bar(lang_counts.head(10), x='count', y='original_language', orientation='h', 
                      template="plotly_dark", color='count', color_continuous_scale=['#2c3440', '#00e054'])
    fig_lang.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False, yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_lang, use_container_width=True)

with col_oc:
    st.subheader("🚩 ORIGINES TOP 10")
    if 'origin_countries' in df_movies_filtered.columns:
        oc_counts = df_movies_filtered.explode('origin_countries')['origin_countries'].value_counts().reset_index()
        fig_oc = px.bar(oc_counts.head(10), x='count', y='origin_countries', orientation='h', 
                        template="plotly_dark", color='count', color_continuous_scale=['#2c3440', '#ff8000'])
        fig_oc.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_oc, use_container_width=True)

# --- CARTE DU MONDE ---
st.divider()
st.subheader("🌍 CARTE DU MONDE DES PRODUCTIONS")
country_counts = df_countries_filtered['country_name'].value_counts().reset_index()
fig_map = px.choropleth(country_counts, locations="country_name", locationmode='country names', color="count",
                        hover_name="country_name", color_continuous_scale=['#1c232b', '#00e054'], template="plotly_dark")
fig_map.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=400, margin={"r":0,"t":0,"l":0,"b":0})
fig_map.update_geos(bgcolor='rgba(0,0,0,0)', showcountries=True, countrycolor="#456")
st.plotly_chart(fig_map, use_container_width=True)

# --- RÉALISATEURS & CASTING ---
st.divider()
col_dir, col_cast = st.columns(2)

with col_dir:
    st.subheader("🎥 TOP RÉALISATEURS")
    dir_stats = df_crew.merge(df_ratings, on=['movie_title', 'release_year'], how='left')
    dir_rank = dir_stats.groupby('name').agg({'movie_title': 'count', 'rating_value': 'mean'}).rename(columns={'movie_title': 'Films vus', 'rating_value': 'Note'}).sort_values('Films vus', ascending=False)
    st.dataframe(dir_rank.head(25).style.format({"Note": "{:.2f}"}), use_container_width=True)

with col_cast:
    st.subheader("🌟 TOP CASTING")
    cast_stats = df_cast.merge(df_ratings, on=['movie_title', 'release_year'], how='left')
    cast_rank = cast_stats.groupby('name').agg({'movie_title': 'count', 'rating_value': 'mean'}).rename(columns={'movie_title': 'Films vus', 'rating_value': 'Note'}).sort_values('Films vus', ascending=False)
    st.dataframe(cast_rank.head(50).style.format({"Note": "{:.2f}"}), use_container_width=True)

# --- SUCCESS & DÉCEPTIONS ---
st.divider()
st.subheader("🏆 SUCCÈS ET DÉCEPTIONS")
df_stats = dfs["mart_rating_stats"]
if selected_year != "Toutes":
    df_stats = df_stats.merge(df_ratings[['movie_title', 'release_year', 'rating_date']], on=['movie_title', 'release_year'])
    df_stats = df_stats[pd.to_datetime(df_stats['rating_date']).dt.year == int(selected_year)]

col_high, col_low = st.columns(2)
with col_high:
    st.markdown("#### ✅ MIEUX NOTÉS QUE VOTRE MOYENNE")
    highs = df_stats[df_stats['comparison'] == 'Higher than average'].sort_values('rating_diff', ascending=False).head(20)
    st.dataframe(highs[['movie_title', 'release_year', 'rating_value', 'rating_diff']].rename(columns={'movie_title': 'Titre', 'rating_value': 'Note', 'rating_diff': 'Diff'}), use_container_width=True)

with col_low:
    st.markdown("#### ❌ MOINS BIEN NOTÉS QUE VOTRE MOYENNE")
    lows = df_stats[df_stats['comparison'] == 'Lower than average'].sort_values('rating_diff', ascending=True).head(20)
    st.dataframe(lows[['movie_title', 'release_year', 'rating_value', 'rating_diff']].rename(columns={'movie_title': 'Titre', 'rating_value': 'Note', 'rating_diff': 'Diff'}), use_container_width=True)

# --- RECOMMANDATIONS & ÉVOLUTION ---
st.divider()
col_rec, col_evol = st.columns(2)

with col_rec:
    st.subheader("🔭 PÉPITES À VOIR (WATCHLIST)")
    df_rec = dfs["mart_watchlist_recommendations"]
    if not df_rec.empty:
        st.dataframe(df_rec[['movie_title', 'release_year', 'tmdb_vote_average']].rename(columns={'movie_title': 'Titre', 'tmdb_vote_average': 'Note TMDB'}).head(20), use_container_width=True)
    else:
        st.info("Aucune recommandation trouvée.")

with col_evol:
    st.subheader("📉 ÉVOLUTION DE VOS NOTES")
    if not df_ratings_filtered.empty:
        df_ratings_filtered['week'] = df_ratings_filtered['rating_date'].dt.to_period('W').apply(lambda r: r.start_time)
        week_stats = df_ratings_filtered.groupby('week')['rating_value'].mean().reset_index()
        fig_evol = px.line(week_stats, x='week', y='rating_value', 
                          template="plotly_dark", color_discrete_sequence=['#40bcf4'],
                          labels={'rating_value': 'Note'})
        fig_evol.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_evol, use_container_width=True)

st.sidebar.title("⚙️ Paramètres")
if st.sidebar.button("Actualiser le Cache", key="refresh_cache_final"):
    st.cache_resource.clear()
    st.rerun()
