import streamlit as st
import pandas as pd
import json
import altair as alt
import hmac
import jwt

data_file_path = "./data/dashboard-data/"

consumption_histories_file_path = data_file_path + "consumption_histories_prod.csv"
organizations_file_path = data_file_path + "organizations_prod.csv"
users_file_path = data_file_path + "users_prod.csv"
contacts_file_path = data_file_path + "contacts_prod.csv"
companies_file_path = data_file_path + "companies_prod.csv"
job_types_file_path = data_file_path + "job_types_prod.csv"
company_sectors_file_path = data_file_path + "company_sectors_prod.csv"
company_sectors_classes_file_path = data_file_path + "company_classes_prod.csv"
company_workforce_file_path = data_file_path + "workforce_prod.csv"
company_sales_file_path = data_file_path + "sales_prod.csv"

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


def check_jwt():
    query_params = st.query_params
    jwt_token = query_params.get("jwt_token", None)
    if jwt_token is None:
        return False
    try:
        decoded = jwt.decode(jwt_token, st.secrets["jwt_public_key"], algorithms=[st.secrets["jwt_algorithm"]])
        # should test here admin_level_id
        return True
    except jwt.ExpiredSignatureError:
        st.error("Le token JWT a expiré.")
    except jwt.InvalidTokenError:
        st.error("Token JWT invalide.")
    return False

no_security = False
try:
    no_security = False if st.secrets["no_security"] == 0 else True
except KeyError:
    no_security = False

if not no_security and not check_jwt() and not check_password():
        st.stop()

@st.cache_data
def load_data_consumption():
    return pd.read_csv(
        consumption_histories_file_path,
        usecols=['id', 'contact_id', 'creation_date', 'organization_id', 'type_id', 'user_id'],
        parse_dates=["creation_date"],
        #nrows=100000
    )

@st.cache_data
def load_data_organization():
    return pd.read_csv(organizations_file_path)

@st.cache_data
def load_data_users():
    return pd.read_csv(users_file_path)

@st.cache_data
def load_data_contact():
    return pd.read_csv(contacts_file_path, usecols=['id', 'company_id', 'tag_list', 'job_type_list'])

@st.cache_data
def load_data_companies():
    return pd.read_csv(companies_file_path, usecols=['id', 'tag_list'])

@st.cache_data
def load_data_company_sectors():
    return pd.read_csv(company_sectors_file_path)

@st.cache_data
def load_data_company_sectors_classes():
    return pd.read_csv(company_sectors_classes_file_path)


@st.cache_data
def load_data_job_types():
    job_types_df = pd.read_csv(job_types_file_path, usecols=['id', 'type'])
    job_types_df = job_types_df.rename(columns={'type': 'name'})
    return job_types_df



@st.cache_data
def load_data_companies_workforce():
    return pd.read_csv(company_workforce_file_path, usecols=['id', 'name'])

@st.cache_data
def load_data_companies_sales():
    return pd.read_csv(company_sales_file_path, usecols=['id', 'name'])



@st.cache_data
def load_format_main_df():
    df = load_data_consumption()
    contacts_df = load_data_contact()
    companies_df = load_data_companies()
    companies_sector_df = load_data_company_sectors()

    # Formating contact data
    contacts_df['job_info'] = contacts_df['job_type_list'].apply(json.loads)
    contacts_df['job_count'] = contacts_df['job_info'].apply(lambda x: len(x)) 
    contacts_df['job_type_id'] = contacts_df['job_info'].apply(lambda x: x[0]['id'] if x else None)

    contacts_df['tags_info'] = contacts_df['tag_list'].apply(json.loads)
    contacts_df['tags_count'] = contacts_df['tags_info'].apply(lambda x: len(x))
    contacts_df['hierarchical_id'] = contacts_df['tags_info'].apply(lambda x: x[0]['list'][0]['id'] if x else None)
    contacts_df['hierarchical_name'] = contacts_df['tags_info'].apply(lambda x: x[0]['list'][0]['name'] if x else None)


    contacts_df.drop(columns=[
        'job_type_list',
        'tag_list',
        'job_info',
        'tags_info',
        'job_count', #
        'tags_count', #
        'hierarchical_id' #
        ], inplace=True)

    df = df.merge(contacts_df, left_on='contact_id', right_on='id', how='left')

    # Formating company data

    # Liste complète des catégories possibles
    all_categories = ["Secteur", "Taille d'entreprise", "Tranche de CA", "Tranche d'effectif", "Structure Type"]

    # Fonction pour extraire les valeurs du JSON stringifié
    def extract_tags(json_str):
        try:
            data = json.loads(json_str)  # Charger le JSON
            flattened_data = {entry["name"]: entry["list"][0]["id"] for entry in data if entry["list"]}
            return {category: flattened_data.get(category, None) for category in all_categories}
        except (json.JSONDecodeError, TypeError):  # Gérer les erreurs de JSON invalide ou NaN
            return {category: None for category in all_categories}

    tags_df = companies_df["tag_list"].apply(extract_tags).apply(pd.Series)

    # Fusionner avec le DataFrame original
    companies_df = pd.concat([companies_df.drop(columns=["tag_list"]), tags_df], axis=1)
    #companies_df = pd.concat([companies_df, tags_df], axis=1) # use the below one afeter debug

    df = df.merge(companies_df, left_on='company_id', right_on='id', how='left')
    #df = df.drop(columns=['id_y']).rename(columns={'id_x': 'id'})
    
    df = df.drop(columns=['id', 'id_y']).rename(columns={'id_x': 'id'})

    df = df.merge(companies_sector_df[['id', 'class']], left_on='Secteur', right_on='id', how='left')
    df = df.drop(columns=['id_y']).rename(columns={'id_x': 'id'})

    return df


df = load_format_main_df()

org_df = load_data_organization()
users_df = load_data_users()
job_types_df = load_data_job_types()

companies_sector_df = load_data_company_sectors()
companies_sector_class_df = load_data_company_sectors_classes()
companies_workforce_df = load_data_companies_workforce()
companies_sales_df = load_data_companies_sales()

org_dict = dict(zip(org_df["name"] + ' (' + org_df["id"].astype(str) + ')' , org_df["id"]))
users_dict = dict(zip(users_df["first_name"] + ' ' + users_df["last_name"] + ' (' + users_df["id"].astype(str) + ')' , users_df["id"]))

type_ids_dict = {
    "consultation contact": 1,
    "exports": 3,
    "exports CRM": 4,
    "location mail": 5,
    "push to crm": 7,
    "campagnes/séquence": 8,
    "mobiles": 9,
}

# Définir la période par défaut (les 31 derniers jours)
default_end_date = df["creation_date"].max()
default_start_date = default_end_date - pd.Timedelta(days=31)


# Interface Streamlit
st.title("Consommation de Données")


st.sidebar.header("Filtres")

# Sélecteurs dates
start_date = st.sidebar.date_input("Date de début", default_start_date)
end_date = st.sidebar.date_input("Date de fin", default_end_date)

# Sélecteur du `type_id`
#type_ids = df["type_id"].unique().tolist()
#selected_type_id = st.sidebar.selectbox("Sélectionner un type_id", type_ids)
selected_type_name = st.sidebar.multiselect("Sélectionner un type", type_ids_dict.keys(), ["consultation contact"])
selected_type_id = [type_ids_dict[name] for name in selected_type_name]


# Sélecteur des organisations (affichage par name, filtrage par id)
selected_org_names = st.sidebar.multiselect("Sélectionner une ou plusieurs organisations", org_dict.keys())

# Conversion des names sélectionnés en id
selected_org_ids = [org_dict[name] for name in selected_org_names]


# Sélecteur des users (affichage par name, filtrage par id)
selected_users_names = st.sidebar.multiselect("Sélectionner un ou plusieurs utilisateurs", users_dict.keys())

# Conversion des names sélectionnés en id
selected_users_ids = [users_dict[name] for name in selected_users_names]


# Affichage par jour ou par mois
#aggregation = st.radio("Afficher par :", ["Jour", "Mois"], index=0)
aggregation = st.selectbox(
    "",
    ("Jour", "Mois"),
    index=0,
)


# Filtrage des données
filtered_df = df[(df["creation_date"] >= pd.Timestamp(start_date)) & (df["creation_date"] <= pd.Timestamp(end_date))]

#filtered_df = filtered_df[filtered_df["type_id"] == selected_type_id]
filtered_df = filtered_df[filtered_df["type_id"].isin(selected_type_id)]


# Filtrage sur les `organization_id`
if selected_org_ids:
    filtered_df = filtered_df[filtered_df["organization_id"].isin(selected_org_ids)]

# Filtrage sur les `user_id`
if selected_users_ids:
    filtered_df = filtered_df[filtered_df["user_id"].isin(selected_users_ids)]


##############################################################
#  CONSOMMATIONS PERIODE GRAPHIQUE HORIZONTAL
##############################################################

# Agrégation des données
if aggregation == "Jour":
    all_dates = pd.date_range(start=start_date, end=end_date, freq="D").date
    grouped_df = filtered_df.groupby(filtered_df["creation_date"].dt.date).size().reset_index(name="count")
    grouped_df = pd.DataFrame({"creation_date": all_dates}).merge(grouped_df, on="creation_date", how="left").fillna(0)
    grouped_df["creation_date"] = grouped_df["creation_date"].astype(str)  # Pour affichage correct
else:
    all_dates = pd.period_range(start=start_date, end=end_date, freq="M")
    grouped_df = filtered_df.groupby(filtered_df["creation_date"].dt.to_period("M")).size().reset_index(name="count")
    grouped_df = pd.DataFrame({"creation_date": all_dates}).merge(grouped_df, on="creation_date", how="left").fillna(0)
    grouped_df["creation_date"] = grouped_df["creation_date"].astype(str)  # Pour affichage correct

primary_color = st.get_option("theme.primaryColor")
background_color = st.get_option("theme.backgroundColor")
text_color = st.get_option("theme.textColor")
secondary_background_color = st.get_option("theme.secondaryBackgroundColor")

# Graphique avec Altair
chart = alt.Chart(grouped_df).mark_bar().encode(
    x=alt.X("creation_date:N", title="Date", sort=None),
    y=alt.Y("count:Q", title="Nombre d'occurrences"),
    tooltip=["creation_date", "count"]
).properties(
    width=800,
    # height=400,
    # title=f"Consommation par {aggregation.lower()}"
)

# Graphique pour les labels
text_labels = alt.Chart(grouped_df).mark_text(
    align="center",
    baseline="bottom",
    dy=-5,  # Décalage vertical pour placer les labels au-dessus des barres
    color=text_color,
    #angle=45
).encode(
    x=alt.X("creation_date:N", sort=None),
    y="count:Q",
    text=alt.Text("count:Q", format=",") 
)

final_chart = (chart + text_labels).configure_axis(
    labelAngle=-45
)

st.altair_chart(final_chart, use_container_width=True)


if selected_org_ids and not selected_users_ids:

    ##############################################################
    #  CHAMPIONS USERS
    ##############################################################
    st.subheader("🥇 Champions de l'organization")
    user_champtions_counts = filtered_df["user_id"].value_counts().reset_index()
    user_champtions_counts.columns = ["user_id", "count"]
    user_champtions_counts = user_champtions_counts.merge(users_df, left_on="user_id", right_on="id", how="left")
    user_champtions_counts["name"] = user_champtions_counts["first_name"] + " " + user_champtions_counts["last_name"] + " (" + user_champtions_counts["id"].astype(str) + ")"
    user_champtions_counts["name"].fillna("Inconnu", inplace=True)

    chart = alt.Chart(user_champtions_counts).mark_bar().encode(
        x=alt.X("count:Q", title="Nombre d'occurrences"),
        y=alt.Y("name:N", title="", sort="-x"),
        tooltip=["name", "count"]
    ).properties(
        #title="Nombre d'occurrences par Tranche d'effectif"
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14,
        labelLimit=300  # Augmente l'espace pour les labels
    )
    st.altair_chart(chart, use_container_width=True)


if not selected_org_ids and not selected_users_ids:

    ##############################################################
    #  CHAMPIONS ORGANIZATIONS
    ##############################################################
    st.subheader("🥇 Top 10 des organizations")

    organizations_champtions_counts = filtered_df["organization_id"].value_counts().reset_index()
    organizations_champtions_counts.columns = ["organization_id", "count"]
    organizations_champtions_counts = organizations_champtions_counts.merge(org_df, left_on="organization_id", right_on="id", how="left")
    organizations_champtions_counts["name"] = organizations_champtions_counts["name"] + " (" + organizations_champtions_counts["id"].astype(str) + ")"
    organizations_champtions_counts["name"].fillna("Inconnu", inplace=True)

    organizations_champtions_counts = organizations_champtions_counts.head(10)

    chart = alt.Chart(organizations_champtions_counts).mark_bar().encode(
        x=alt.X("count:Q", title="Nombre d'occurrences"),
        y=alt.Y("name:N", title="", sort="-x"),
        tooltip=["name", "count"]
    ).properties(
        #title="Nombre d'occurrences par Tranche d'effectif"
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14,
        labelLimit=300  # Augmente l'espace pour les labels
    )
    st.altair_chart(chart, use_container_width=True)


st.dataframe(df.head(1000))


##############################################################
#  FAMILLE DE FONCTIONS
##############################################################

st.subheader("👔 Répartition par famille de fonction")
job_counts = filtered_df["job_type_id"].value_counts().reset_index()
job_counts.columns = ["job_type_id", "count"]
job_counts = job_counts.merge(job_types_df, left_on="job_type_id", right_on="id", how="left")
job_counts["name"].fillna("Inconnu", inplace=True)

chart = alt.Chart(job_counts).mark_bar().encode(
    x=alt.X("count:Q", title="Nombre d'occurrences"),
    y=alt.Y("name:N", title="", sort="-x"),
    tooltip=["name", "count"],
).properties(
    width=700,
)

text_labels = alt.Chart(job_counts).mark_text(
    align="left",
    baseline="middle",
    dx=5,
    color=text_color
).encode(
    x=alt.X("count:Q", title="Nombre d'occurrences"),
    y=alt.Y("name:N", title="", sort="-x"),
    text=alt.Text("count:Q", format=",") 
)

final_chart = (chart + text_labels).configure_axis(
    labelFontSize=12,
    titleFontSize=14,
    labelLimit=300
)

st.altair_chart(final_chart, use_container_width=True)






##############################################################
#  Hierarchical name
##############################################################
st.subheader("🔝 Niveau hierarchique")

hierarchical_counts = filtered_df["hierarchical_name"].value_counts().reset_index()
hierarchical_counts.columns = ["hierarchical_name", "count"]

total_count = hierarchical_counts["count"].sum()
hierarchical_counts["rate"] = (hierarchical_counts["count"] / total_count) * 100
hierarchical_counts["rate"] = hierarchical_counts["rate"].round(2)
hierarchical_counts['rate_with_units'] = hierarchical_counts['rate'].apply(lambda x: f"{x:,.0f} %")
chart = alt.Chart(hierarchical_counts).mark_bar().encode(
    x=alt.X("count:Q", title="Nombre d'occurrences"),
    y=alt.Y("hierarchical_name:N", title="", sort="-x"),
    tooltip=["hierarchical_name", "count"]
)

text_labels = alt.Chart(hierarchical_counts).mark_text(
    align="left",
    baseline="middle",
    dx=5,
    color=text_color
).encode(
    x=alt.X("count:Q", title="Nombre d'occurrences"),
    y=alt.Y("hierarchical_name:N", title="", sort="-x"),
    text=alt.Text("count:Q", format=",") 
)
final_chart = (chart + text_labels).configure_axis(
    labelFontSize=12,
    titleFontSize=14,
    labelLimit=300
)
st.altair_chart(final_chart, use_container_width=True)

######
chart = alt.Chart(hierarchical_counts).mark_bar().encode(
    x=alt.X("rate:Q", title="Nombre d'occurrences"),
    y=alt.Y("hierarchical_name:N", title="", sort="-x"),
    tooltip=["hierarchical_name", "rate"]
)

text_labels = alt.Chart(hierarchical_counts).mark_text(
    align="left",
    baseline="middle",
    dx=5,
    color=text_color
).encode(
    x=alt.X("rate:Q", title="Nombre d'occurrences"),
    y=alt.Y("hierarchical_name:N", title="", sort="-x"),
    text="rate_with_units"
)

final_chart = (chart + text_labels).configure_axis(
    labelFontSize=12,
    titleFontSize=14,
    labelLimit=300
)
st.altair_chart(final_chart, use_container_width=True)





# Créer un pie chart avec Altair
pie_chart = alt.Chart(hierarchical_counts).mark_arc().encode(
    theta=alt.Theta(field="count", type="quantitative"),
    color=alt.Color(field="hierarchical_name", type="nominal"),
    tooltip=["hierarchical_name", "count"]
).properties(
    width=400,
    height=400,
    title="Répartition des catégories"
)
st.altair_chart(pie_chart, use_container_width=True)



##############################################################
#  Workforce
##############################################################

# Workforce
st.subheader("👷 Répartition par Tranche d'effectif")

workforce_counts = filtered_df["Tranche d'effectif"].value_counts().reset_index()
workforce_counts.columns = ["Tranche d'effectif", "count"]
workforce_counts = workforce_counts.merge(companies_workforce_df, left_on="Tranche d'effectif", right_on="id", how="left")
workforce_counts["name"].fillna("Inconnu", inplace=True)

chart = alt.Chart(workforce_counts).mark_bar().encode(
    x=alt.X("count:Q", title="Nombre d'occurrences"),
    y=alt.Y("name:N", title="", sort="-x"),
    tooltip=["name", "count"]
)

text_labels = alt.Chart(workforce_counts).mark_text(
    align="left",
    baseline="middle",
    dx=5,
    color=text_color
).encode(
    x=alt.X("count:Q", title="Nombre d'occurrences"),
    y=alt.Y("name:N", title="", sort="-x"),
    text=alt.Text("count:Q", format=",") 
)

final_chart = (chart + text_labels).configure_axis(
    labelFontSize=12,
    titleFontSize=14,
    labelLimit=300
)

st.altair_chart(final_chart, use_container_width=True)


##############################################################
#  Tranches CA
##############################################################

st.subheader("💵 Répartition par Tranche de CA")
company_sales_counts = filtered_df["Tranche de CA"].value_counts().reset_index()
company_sales_counts.columns = ["Tranche de CA", "count"]
company_sales_counts = company_sales_counts.merge(companies_sales_df, left_on="Tranche de CA", right_on="id", how="left")
company_sales_counts["name"].fillna("Inconnu", inplace=True)

chart = alt.Chart(company_sales_counts).mark_bar().encode(
    x=alt.X("count:Q", title="Nombre d'occurrences"),
    y=alt.Y("name:N", title="", sort="-x"),
    tooltip=["name", "count"]
)

text_labels = alt.Chart(company_sales_counts).mark_text(
    align="left",
    baseline="middle",
    dx=5,
    color=text_color
).encode(
    x=alt.X("count:Q", title="Nombre d'occurrences"),
    y=alt.Y("name:N", title="", sort="-x"),
    text=alt.Text("count:Q", format=",") 
)

final_chart = (chart + text_labels).configure_axis(
    labelFontSize=12,
    titleFontSize=14,
    labelLimit=300
)

st.altair_chart(final_chart, use_container_width=True)



##############################################################
#  Secteurs (Secteurs types)
##############################################################

st.subheader("💼 Répartition par méta secteur")
meta_sector_counts = filtered_df["class"].value_counts().reset_index()
meta_sector_counts.columns = ["class", "count"]
meta_sector_counts = meta_sector_counts.merge(companies_sector_class_df, left_on="class", right_on="id", how="left")
meta_sector_counts["name"].fillna("Inconnu", inplace=True)

chart = alt.Chart(meta_sector_counts).mark_bar().encode(
    x=alt.X("count:Q", title="Nombre d'occurrences"),
    y=alt.Y("name:N", title="", sort="-x"),
    tooltip=["name", "count"]
)

text_labels = alt.Chart(meta_sector_counts).mark_text(
    align="left",
    baseline="middle",
    dx=5,
    color=text_color
).encode(
    x=alt.X("count:Q", title="Nombre d'occurrences"),
    y=alt.Y("name:N", title="", sort="-x"),
    text=alt.Text("count:Q", format=",") 
)

final_chart = (chart + text_labels).configure_axis(
    labelFontSize=12,
    titleFontSize=14,
    labelLimit=300
)

st.altair_chart(final_chart, use_container_width=True)



##############################################################
#  Secteurs (Secteurs types)
##############################################################
st.subheader("🏭 Répartition par secteur")
sector_counts = filtered_df["Secteur"].value_counts().reset_index()
sector_counts.columns = ["Secteur", "count"]
sector_counts = sector_counts.merge(companies_sector_df, left_on="Secteur", right_on="id", how="left")
sector_counts["name"].fillna("Inconnu", inplace=True)

chart = alt.Chart(sector_counts).mark_bar().encode(
    x=alt.X("count:Q", title="Nombre d'occurrences"),
    y=alt.Y("name:N", title="", sort="-x"),
    tooltip=["name", "count"]
)

text_labels = alt.Chart(sector_counts).mark_text(
    align="left",
    baseline="middle",
    dx=5,
    color=text_color
).encode(
    x=alt.X("count:Q", title="Nombre d'occurrences"),
    y=alt.Y("name:N", title="", sort="-x"),
    text=alt.Text("count:Q", format=",") 
)

final_chart = (chart + text_labels).configure_axis(
    labelFontSize=12,
    titleFontSize=14,
    labelLimit=300
)
st.altair_chart(final_chart, use_container_width=True)



#st.dataframe(df.head())


