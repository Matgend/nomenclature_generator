import streamlit as st
import pandas as pd
import os

@st.cache_data
def load_data():
    """Charge toutes les feuilles Excel"""
    excel_path = './nomenclature.xlsx'

    if not os.path.exists(excel_path):
        st.error(f'Fichier non trouvé: {excel_path}')
        return None, None, None, None, None, None, None, None, None, None, None
    
    try:
        # Charger toutes les feuilles
        df_item = pd.read_excel(excel_path, sheet_name = 'ARTICLE')
        df_classe = pd.read_excel(excel_path, sheet_name = 'CLASSIFICATION_ARTICLE')
        
        # Tables de référence
        df_type = pd.read_excel(excel_path, sheet_name = 'TYPE', skiprows = [0])
        df_usage = pd.read_excel(excel_path, sheet_name = 'USAGE', skiprows = [0])
        df_fonction = pd.read_excel(excel_path, sheet_name = 'FONCTION', skiprows = [0])
        df_materiau = pd.read_excel(excel_path, sheet_name = 'MATERIAU', skiprows = [0])
        
        # Tables de liaison
        df_type_item = pd.read_excel(excel_path, sheet_name = 'TYPE_SOUS_FAMILLE')
        df_usage_item = pd.read_excel(excel_path, sheet_name = 'USAGE_SOUS_FAMILLE')
        df_fonction_item = pd.read_excel(excel_path, sheet_name = 'FONCTION_SOUS_FAMILLE')
        df_materiau_item = pd.read_excel(excel_path, sheet_name = 'MATERIAU_SOUS_FAMILLE')
        
        # Autres tables
        df_mesure = pd.read_excel(excel_path, sheet_name = 'MESURE')
        df_unite = pd.read_excel(excel_path, sheet_name = 'UNITE_GROUPE')

        # Nettoyer les noms des colonnes
        for df in [df_item, df_classe, df_type, df_usage, df_fonction, df_materiau, 
                   df_type_item, df_usage_item, df_fonction_item, df_materiau_item, 
                   df_mesure, df_unite]:
            if not df.empty:
                df.columns = df.columns.str.strip()
        
        return (df_item, df_classe, df_type, df_usage, df_fonction, df_materiau,
                df_type_item, df_usage_item, df_fonction_item, df_materiau_item,
                df_mesure, df_unite)
    
    except Exception as e:
        st.error(f'Erreur de chargement: {e}')
        return None, None, None, None, None, None, None, None, None, None, None, None
    

def get_attr_display_label(attr, df):
    """Libellé lisible pour un attribut : résout les codes MEA_x vers leur
    nom de mesure (ex: 'MEA_2' -> 'Conditionnement'). Le code brut `attr`
    reste inchangé partout ailleurs (détection startswith('MEA_'), clés
    de session_state, etc.) — seul l'affichage change."""
    if attr.startswith('MEA_') and df is not None and not df.empty:
        mesure_row = df[df['ID'] == attr]
        if not mesure_row.empty:
            return str(mesure_row.iloc[0].get('MESURE', attr))
    return attr


def find_lang_columns(df):
    """Détecte automatiquement les colonnes FR/EN d'une table de référence."""
    fra_col, en_col = None, None
    for col in df.columns:
        col_up = str(col).upper()
        if 'FRA' in col_up and fra_col is None:
            fra_col = col
        elif 'ENG' in col_up and en_col is None:
            en_col = col
    return fra_col, en_col