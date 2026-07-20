# app_streamlit.py - Version corrigée
import streamlit as st
import pandas as pd
import re
from utils import load_data, get_attr_display_label, find_lang_columns

# Configuration de la page
st.set_page_config(
    page_title='Générateur nomenclature Articles',
    layout='wide'
)

# ---------------------------------------------------------------------------
# Chargement des données
# ---------------------------------------------------------------------------
(df_item, df_classe, df_type, df_usage, df_fonction, df_materiau,
 df_type_item, df_usage_item, df_fonction_item, df_materiau_item,
 df_mesure, df_unite) = load_data()

if df_item is None:
    st.stop()

print(df_item)

# Titre
st.title('Générateur de description')
st.markdown('---')

# Sidebar avec informations
with st.sidebar:
    st.header('Instructions')
    st.markdown('''
    1. Sélectionnez un **Article**
    2. Choisissez **Sans Marque** ou **Marque**
    3. Remplissez les **attributs** demandés
    4. Cliquez sur **Générer**
    ''')
    st.markdown('---')
    st.caption('v1.2 - Sodimex')

# ---------------------------------------------------------------------------
# Initialisation de session_state
# ---------------------------------------------------------------------------
if 'attribute_values' not in st.session_state:
    st.session_state.attribute_values = {}
if 'brand' not in st.session_state:
    st.session_state.brand = ""
if 'last_selected_item' not in st.session_state:
    st.session_state.last_selected_item = None


# Liste unique des sous-familles
item_unique = df_classe[['ARTICLE_VALUE_FRA', 'ARTICLE_VALUE_ENG']].drop_duplicates(subset=['ARTICLE_VALUE_FRA'])
item_list = sorted(item_unique['ARTICLE_VALUE_FRA'].tolist())

selected_item = st.selectbox(
    "**Sélectionnez un type d'ARTICLE**",
    item_list,
    help="Choisissez l'article",
    key='main_item_select'
)

# Réinitialiser les valeurs saisies quand on change d'article, pour éviter
# qu'un ancien attribut (ex: "Type") ne pré-remplisse un article différent.
if selected_item != st.session_state.last_selected_item:
    st.session_state.attribute_values = {}
    st.session_state.brand = ""
    st.session_state.last_selected_item = selected_item

if selected_item:
    # Récupérer toutes les lignes pour cet article
    item_rows = df_classe[df_classe['ARTICLE_VALUE_FRA'] == selected_item]

    # Options disponibles pour GENERIC (bool attendu ; on tolère aussi les
    # valeurs manquantes/NaN sans planter)
    generic_options = item_rows['GENERIC'].dropna().unique().tolist()
    has_generic_true = True in generic_options
    has_generic_false = False in generic_options

    st.subheader("Type d'article")

    col1, col2 = st.columns([1, 2])
    with col1:
        if has_generic_true and has_generic_false:
            generic_choice = st.radio(
                "Choix",
                ["GENERIC", "Avec marque|référence"],
                index=0,
                key="generic_choice"
            )
            is_generic = (generic_choice == "GENERIC")
        elif has_generic_true:
            st.info("Cet article est uniquement disponible en version GENERIC")
            is_generic = True
        elif has_generic_false:
            st.info("Cet article nécessite une marque et une référence")
            is_generic = False
        else:
            st.error(
                "Aucune configuration GENERIC/Marque définie pour cet article dans "
                "CLASSIFICATION_ARTICLE. Vérifiez la colonne GENERIC."
            )
            st.stop()

    brand = ''
    if not is_generic:
        with col2:
            brand = st.text_input(
                "**Marque | Référence fournisseur**",
                value=st.session_state.brand,
                placeholder="Ex: CATERPILLAR|375-4479, CATERPILLAR|37-4479, BOSCH|GBH 2-26 DRE",
                key="brand_input"
            )
            st.session_state.brand = brand

    # Sélectionner la ligne correspondant au choix GENERIC, avec garde-fou
    matching_rows = item_rows[item_rows['GENERIC'] == is_generic]
    if matching_rows.empty:
        st.error(
            f"Aucune ligne CLASSIFICATION_ARTICLE ne correspond à "
            f"'{selected_item}' avec GENERIC={is_generic}. Vérifiez le fichier source."
        )
        st.stop()
    selected_row = matching_rows.iloc[0]

    # -----------------------------------------------------------------
    # Récupérer les attributs à remplir (D1 à D9)
    # On garde les codes bruts (ex: "MEA_2") tels quels ; la traduction en
    # libellé se fait uniquement à l'AFFICHAGE, pas ici, pour ne pas casser
    # la détection "startswith('MEA_')" plus loin.
    # -----------------------------------------------------------------
    attributs = []
    attr_source_col = []  # colonne D d'origine de chaque attribut (ex: 'D3'), même longueur que `attributs`
    mandatory_col = 'OBLIGATOIRE/MANDATORY'
    for i in range(1, 10):
        col_name = f'D{i}'
        if col_name in selected_row.index and pd.notna(selected_row[col_name]):
            value_str = str(selected_row[col_name])
            if ';' in value_str:
                parts = [v.strip() for v in value_str.split(';')]
            else:
                parts = [value_str]
            for p in parts:
                if p and p != 'nan':
                    attributs.append(p)
                    attr_source_col.append(col_name)

    # Détermine quels attributs sont "importants" (obligatoires).
    # La colonne OBLIGATOIRE/MANDATORY liste les colonnes Dx concernées
    # (ex: "D4" ou "D2;D7;D8"). Quand elle est renseignée, seules ces
    # colonnes sont obligatoires ; sinon on considère tous les attributs
    # de la ligne comme importants par défaut.
    mandatory_cols = set()
    if mandatory_col in selected_row.index and pd.notna(selected_row[mandatory_col]):
        mandatory_cols = {c.strip() for c in str(selected_row[mandatory_col]).split(';') if c.strip()}

    if mandatory_cols:
        is_mandatory_list = [col in mandatory_cols for col in attr_source_col]
    else:
        is_mandatory_list = [True] * len(attributs)

    st.subheader('Attributs à définir')
    st.markdown("Remplissez les informations suivantes dans l'ordre. "
                 "Les attributs marqués :red[**\\***] sont importants.")

    if not attributs:
        st.info("Aucun attribut à définir pour cet article")
    else:
        summary_parts = []
        for a, mand in zip(attributs, is_mandatory_list):
            label = get_attr_display_label(a, df_mesure)
            summary_parts.append(f"**{label}** :red[*]" if mand else label)
        st.markdown(f"**Attributs à remplir:** {', '.join(summary_parts)}")

        attribut_values = {}

        # Dictionnaire pour mapper les attributs aux tables de référence.
        # value_col_hint sert juste de mémo ; les vraies colonnes FR/EN sont
        # détectées dynamiquement via find_lang_columns().
        attr_mapping = {
            'Type': {'liaison': df_type_item, 'ref': df_type, 'id_col': 'ID_TYPE', 'item_col': 'ID_ITEM'},
            'Usage': {'liaison': df_usage_item, 'ref': df_usage, 'id_col': 'ID_USAGE', 'item_col': 'ID_ITEM'},
            'Fonction': {'liaison': df_fonction_item, 'ref': df_fonction, 'id_col': 'ID_FONCTION', 'item_col': 'ID_ITEM'},
            'Materiau': {'liaison': df_materiau_item, 'ref': df_materiau, 'id_col': 'ID_MATERIAU', 'item_col': 'ID_ITEM'},
        }

        item_id = selected_row.get('ID_ARTICLE') if 'ID_ARTICLE' in selected_row.index else None

        for idx, attr in enumerate(attributs):
            unique_key = f"{attr}_{idx}_{str(selected_item).replace(' ', '_')}"
            is_mandatory = is_mandatory_list[idx]
            display_label = get_attr_display_label(attr, df_mesure)
            widget_label = f'**{display_label}** :red[*]' if is_mandatory else f'{display_label} _(optionnel)_'

            # Cas 1: ITEM_VALUE (valeur de l'article lui-même)
            if attr.upper() == 'ITEM_VALUE':
                st.text_input(
                    widget_label,
                    value=selected_item,
                    disabled=True,
                    key=unique_key,
                    help="Valeur par défaut de la sous-famille"
                )
                attribut_values[attr] = selected_item
                continue

            # Cas 2: Attribut avec liaison (Type, Usage, Fonction, Materiau)
            if attr in attr_mapping and item_id is not None:
                mapping = attr_mapping[attr]
                df_liaison = mapping['liaison']
                df_ref = mapping['ref']
                rendered = False
                if df_liaison is not None and not df_liaison.empty and df_ref is not None and not df_ref.empty:
                    
                    if mapping['item_col'] in df_liaison.columns:
                        filtered_ids = df_liaison[df_liaison[mapping['item_col']] == item_id][mapping['id_col']].tolist()
                        if filtered_ids:
                            filtered_ref = df_ref[df_ref[mapping['id_col']].isin(filtered_ids)]
                            fra_col, en_col = find_lang_columns(filtered_ref)
                            if fra_col:
                                options = filtered_ref[fra_col].dropna().unique().tolist()
                                options = [str(o) for o in options]
                                if options:
                                    prev_value = st.session_state.attribute_values.get(attr, "")
                                    default_index = options.index(prev_value) if prev_value in options else 0
                                    selected_value = st.selectbox(
                                        widget_label,
                                        options,
                                        index=default_index,
                                        key=unique_key,
                                        help=f'Sélectionnez la valeur pour {attr}'
                                    )
                                    if selected_value:
                                        attribut_values[attr] = selected_value
                                        st.session_state.attribute_values[attr] = selected_value
                                    rendered = True

                if not rendered:
                    st.warning(
                        f"Aucune option trouvée pour **{attr}** (article '{selected_item}'). "
                        f"Vérifiez la table de liaison correspondante."
                    )
                continue

            # Cas 3: Mesure (MEA_X)
            if attr.startswith('MEA_') and df_mesure is not None and not df_mesure.empty:
                mesure_row = df_mesure[df_mesure['ID'] == attr]
                if not mesure_row.empty:
                    measure_name = mesure_row.iloc[0].get('MESURE', attr)
                    exemple = mesure_row.iloc[0].get('EXEMPLE', '')

                    col1, col2 = st.columns(2)
                    with col1:
                        prev_full = st.session_state.attribute_values.get(attr, "")
                        prev_numeric = ""
                        if prev_full:
                            match = re.match(r'^([\d.]+)', str(prev_full))
                            if match:
                                prev_numeric = match.group(1)

                        measure_label = f'**{measure_name}** :red[*]' if is_mandatory else f'{measure_name} _(optionnel)_'
                        value = st.text_input(
                            measure_label,
                            value=prev_numeric,
                            placeholder=f"Ex: {exemple}",
                            key=f"value_{unique_key}",
                            help=f'Entrez la valeur numérique pour {measure_name}'
                        )

                    with col2:
                        unite_ids = str(mesure_row.iloc[0].get('UNITE', '')).split(';')
                        unites = []
                        if unite_ids and df_unite is not None and not df_unite.empty:
                            unite_id_col = 'ID UNITE' if 'ID UNITE' in df_unite.columns else 'ID'
                            if unite_id_col in df_unite.columns:
                                unites = [str(u) for u in
                                          df_unite[df_unite[unite_id_col].isin(unite_ids)]['UNITE_FRA'].dropna().tolist()]

                        if unites:
                            prev_full = st.session_state.attribute_values.get(attr, "")
                            prev_unite = next((u for u in unites if u in str(prev_full)), "")
                            default_index = unites.index(prev_unite) if prev_unite in unites else 0

                            unite = st.selectbox(
                                'Unité',
                                unites,
                                index=default_index,
                                key=f"unite_{unique_key}",
                                help="Sélectionnez l'unité de mesure"
                            )
                            if value and unite:
                                full_value = f"{value} {unite}"
                                attribut_values[attr] = full_value
                                st.session_state.attribute_values[attr] = full_value
                            elif value:
                                attribut_values[attr] = value
                                st.session_state.attribute_values[attr] = value
                        elif value:
                            attribut_values[attr] = value
                            st.session_state.attribute_values[attr] = value
                    continue
                else:
                    st.warning(f"Code de mesure inconnu: {attr}")
                    continue

            # Cas 4: Attribut simple avec texte libre
            prev_value = st.session_state.attribute_values.get(attr, "")
            text_value = st.text_input(
                widget_label,
                value=prev_value,
                placeholder=f'Entrez la valeur pour {attr}',
                key=f"text_{unique_key}",
                help=f'Saisissez la valeur pour {attr}'
            )
            if text_value:
                attribut_values[attr] = text_value
                st.session_state.attribute_values[attr] = text_value

        # -------------------------------------------------------------
        # Génération
        # -------------------------------------------------------------
        st.markdown('   ')
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            generate_button = st.button(
                '**Générer la nomenclature**',
                use_container_width=True,
                type='primary',
                key='generate_btn'
            )

            if generate_button:
                missing = [
                    get_attr_display_label(a) for a, mand in zip(attributs, is_mandatory_list)
                    if mand and (a not in attribut_values or not str(attribut_values[a]).strip())
                ]
                if missing:
                    st.error(
                        "Merci de renseigner les attributs importants avant de générer : "
                        + ', '.join(missing)
                    )
                else:
                    # Construction dans l'ordre exact de `attributs` (on ignore
                    # les attributs optionnels laissés vides).
                    name_parts = [
                        str(attribut_values[a]).strip()
                        for a in attributs
                        if a in attribut_values and str(attribut_values[a]).strip()
                    ]

                    if not is_generic and brand:
                        name_parts.append(f'- {brand} -')
                    if is_generic:
                        name_parts.append('- GENERIC -')

                    if 'UNITE_SAGEX3' in selected_row.index and pd.notna(selected_row['UNITE_SAGEX3']):
                        unite_sage = str(selected_row['UNITE_SAGEX3']).strip()
                        if unite_sage and unite_sage != 'nan':
                            name_parts.append(f'[{unite_sage}]')

                    nomenclature = ' '.join(name_parts)

                    st.markdown('---')
                    st.subheader('Résultat')
                    st.code(nomenclature, language='text')

                    st.markdown('''
                    <div style="text-align: center; margin-top: 10px;">
                        <small>💡 Astuce: Sélectionnez le texte et faites Ctrl+C pour copier</small>
                    </div>
                    ''', unsafe_allow_html=True)

# Footer
st.markdown('---')
st.caption('Générateur de nomenclature automatique basé sur les règles groupes')