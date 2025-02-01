import streamlit as st
import pandas as pd
import altair as alt


consumption_histories_file_path = "/home/artiom/Bureau/dashboard-data/consumption_histories_prod.csv"
org_file_path = "/home/artiom/Bureau/dashboard-data/organizations_prod.csv"


@st.cache_data
def load_data_consumption():
    return pd.read_csv(consumption_histories_file_path, parse_dates=["creation_date"])


@st.cache_data
def load_data_organization():
    return pd.read_csv(org_file_path)



df = load_data_consumption()
org_df = load_data_organization()

org_dict = dict(zip(org_df["name"], org_df["id"]))

# Définir la période par défaut (les 31 derniers jours)
default_end_date = df["creation_date"].max()
default_start_date = default_end_date - pd.Timedelta(days=31)

#st.write("Aperçu des données :")
#st.dataframe(df.head())

# Interface Streamlit
st.title("Consommation de Données")

# Sélecteurs
st.sidebar.header("Filtres")
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
aggregation = st.sidebar.radio("Afficher par :", ["Jour", "Mois"], index=0)

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