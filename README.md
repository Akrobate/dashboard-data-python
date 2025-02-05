# dashboard-data-python

## Description

Simple project to test `streamlit` dashboard framework. Based on an event like data source it can filter on period, select specific filters, and render data visualisation with different group axes.

## Security

Two different methods of access is enabled. Data viz can be protected by a simple password or a valid JWT Key.

### Set password

in root of the app create `.strealit/secrets.toml`

```
password = "mypassword"
jwt_public_key = ""
jwt_algorithm = ""
```

## Install

```bash
python3 -m virtualenv venv
source venv/bin/activate
pip install streamlit pyjwt
streamlit run app.py
```

## Prepare user data

User data must be stored in mounted data folder `./data`


