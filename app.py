import streamlit as st
import pandas as pd
import json
import altair as alt

data_file_path = "../../Bureau/dashboard-data/"

consumption_histories_file_path = data_file_path + "consumption_histories_prod.csv"
organizations_file_path = data_file_path + "organizations_prod.csv"
users_file_path = data_file_path + "users_prod.csv"
contacts_file_path = data_file_path + "contacts_prod.csv"


@st.cache_data
def load_data_consumption():
    return pd.read_csv(consumption_histories_file_path, parse_dates=["creation_date"])

@st.cache_data
def load_data_organization():
    return pd.read_csv(organizations_file_path)

@st.cache_data
def load_data_users():
    return pd.read_csv(users_file_path)

@st.cache_data
def load_data_contact():
    return pd.read_csv(contacts_file_path)


df = load_data_consumption()
org_df = load_data_organization()
users_df = load_data_users()
contacts_df = load_data_contact()

contacts_df['job_info'] = contacts_df['job_type_list'].apply(json.loads)
contacts_df['job_count'] = contacts_df['job_info'].apply(lambda x: len(x)) 
contacts_df['job_type_id'] = contacts_df['job_info'].apply(lambda x: x[0]['id'] if x else None)

contacts_df['tags_info'] = contacts_df['tag_list'].apply(json.loads)
contacts_df['tags_count'] = contacts_df['tags_info'].apply(lambda x: len(x))
contacts_df['hierarchical_id'] = contacts_df['tags_info'].apply(lambda x: x[0]['list'][0]['id'] if x else None)
contacts_df['hierarchical_name'] = contacts_df['tags_info'].apply(lambda x: x[0]['list'][0]['name'] if x else None)

contacts_df.drop(columns=[
    'civility_id',
    'has_direct_phone',
    'has_email',
    'has_mobile_phone',
    'job_start_date',
    'job_title',
    'email',
    'job_type_list',
    'first_name',
    'last_name',
    'created_at',
    'updated_at',
    'optout',
    'tag_list',
    'is_visible_pme',
    'has_standard_phone',
    'address_city',
    'address_department',
    'job_info',
    'tags_info',
    'job_count', #
    'tags_count', #
    'hierarchical_id' #
    ], inplace=True)


df = df.merge(contacts_df, left_on='contact_id', right_on='id', how='left')
#df_merged = df_merged.drop(columns=['id_y']).rename(columns={'id_x': 'id'})


org_dict = dict(zip(org_df["name"] + ' (' + org_df["id"].astype(str) + ')' , org_df["id"]))

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
type_ids = df["type_id"].unique().tolist()
selected_type_id = st.sidebar.selectbox("Sélectionner un type_id", type_ids)

# Sélecteur des organisations (affichage par name, filtrage par id)
selected_org_names = st.sidebar.multiselect("Sélectionner une ou plusieurs organisations", org_dict.keys())

# Conversion des names sélectionnés en id
selected_org_ids = [org_dict[name] for name in selected_org_names]

# Affichage par jour ou par mois
aggregation = st.radio("Afficher par :", ["Jour", "Mois"], index=0)

# Filtrage des données
filtered_df = df[(df["creation_date"] >= pd.Timestamp(start_date)) & (df["creation_date"] <= pd.Timestamp(end_date))]
filtered_df = filtered_df[filtered_df["type_id"] == selected_type_id]


# Filtrage sur les `organization_id`
if selected_org_ids:
    filtered_df = filtered_df[filtered_df["organization_id"].isin(selected_org_ids)]



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

# Graphique avec Altair
chart = alt.Chart(grouped_df).mark_bar().encode(
    x=alt.X("creation_date:N", title="Date", sort=None),
    y=alt.Y("count:Q", title="Nombre d'occurrences"),
    tooltip=["creation_date", "count"]
).properties(
    width=800,
    height=400,
    title=f"Consommation par {aggregation.lower()}"
).configure_axis(
    labelAngle=-45
)

st.altair_chart(chart, use_container_width=True)

st.write("Aperçu des données :")
st.dataframe(df.head())


st.write("Aperçu des contacts_df :")
st.dataframe(contacts_df)
