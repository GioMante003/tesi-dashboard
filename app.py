import dash
import dash_bootstrap_components as dbc
import pandas as pd
import json
import plotly.express as px
from dash import dcc, html, Input, Output
from dash.exceptions import PreventUpdate
from dash import callback, Input, Output, State, ctx, no_update



# === Percorso dati ===
folder = "/Users/giorgiomantero/Documents/UniGio/Tesi/tesi-dashboardgit/"
geojson_path = folder + "limiti_province_italia.geojson"

# Carica CSV
df = pd.read_csv('Lista_incubatori_categorie.csv')
df.loc[df['comune'].str.upper() == "NAPOLI", 'pv'] = "NA"

df = df.drop(columns=[col for col in ["codice fiscale", "settore", "sito internet", "attività", "ateco 2007"] if col in df.columns])

# === Area geografica ===
nord = [
    'BI', 'BO', 'BS', 'BZ', 'CO', 'FC', 'GE', 'MI', 'PD', 'PN', 'TN',
    'TO', 'TR', 'TS', 'TV', 'UD', 'VE', 'VR'
]

centro = [
    'AN', 'AQ', 'MC', 'PI', 'PU', 'RM', 'SI'
]

sud = [
    'AV', 'BA', 'BN', 'CA', 'CE', 'CZ', 'FG', 'LE', 'NA', 'PZ', 'SS', 'TP'
]

def area_geografica(pv):
    if pv in nord:
        return 'Nord'
    elif pv in centro:
        return 'Centro'
    elif pv in sud:
        return 'Sud'



df["area_geografica"] = df["pv"].apply(area_geografica)

# === GeoJSON ===
def load_geojson(path):
    with open("limiti_province_italia.geojson", encoding="utf-8") as f:
        return json.load(f)

gj_province = load_geojson(geojson_path)
province_geojson = [f["properties"]["prov_acr"] for f in gj_province["features"]]

df_raw_counts = df.groupby("pv").size().reset_index(name="n_incubatori")
df_raw_counts.rename(columns={"pv": "provincia"}, inplace=True)

df_all_province = pd.DataFrame({'provincia': province_geojson})
df_counts = df_all_province.merge(df_raw_counts, on="provincia", how="left")
df_counts["n_incubatori"] = df_counts["n_incubatori"].fillna(0).astype(int)

header_style = {
    'fontWeight': 'bold',
    'fontSize': '18px',
    'padding': '6px 12px',
    'color': '#003366',
    'minHeight': '40px',
    'display': 'flex',
    'alignItems': 'center'
}

# === APP ===
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server  # <- Questa riga è fondamentale per Render!

# Layout
app.layout = dbc.Container([
    # Titolo
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H2(
                    "📊 Cruscotto Interattivo sugli Incubatori Certificati",
                    style={
                        'textAlign': 'center',
                        'fontWeight': 'bold',
                        'color': '#003366',
                        'fontSize': '30px',
                        'marginTop': '20px'
                    }
                ),
                html.H6([
                    "Analisi grafica dei dati relativi agli incubatori italiani presenti nel ",
                    html.A(
                        "Registro delle Imprese",
                        href="https://startup.registroimprese.it/isin/static/startup/index.html?slideJump=33",
                        target="_blank",
                        style={'color': '#003366', 'textDecoration': 'underline'}
                    )
                ],
                style={
                    'textAlign': 'center',
                    'color': '#666666',
                    'fontStyle': 'italic',
                    'marginBottom': '25px'
                })
            ])
        ])
    ]),


    # Prima riga, prima colonna MAPPA
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Mappa degli incubatori per provincia", style=header_style),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Row([
                                dbc.Col(html.Label("Filtra per natura giuridica:", style={'fontWeight': 'bold'}), width="auto"),
                                dbc.Col(dcc.Dropdown(
                                    id='filtro_natgiuridica',
                                    options=[{'label': n, 'value': n} for n in sorted(df['nat.giuridica'].dropna().unique())],
                                    value=None,
                                    placeholder="Seleziona una natura giuridica",
                                    style={'width': '450px'}
                                ), width="auto")
                            ], align="center"),
                            html.Div(id="output_numero_incubatori",
                                     style={'fontWeight': 'bold', 'color': '#333333', 'fontSize': '16px', 'marginTop': '12px'})
                        ])
                    ], className="mt-3 mb-3"),
                    html.Div(
                        dcc.Graph(id='map_incubatori', style={'height': '450px', 'width': '100%'}),
                        style={'flexGrow': 1}
                    )
                ], style={'padding': '6px', 'height': '100%', 'display': 'flex', 'flexDirection': 'column'})
            ], style={"height": "100%"})
        ], width=6),
        # Prima riga, seconda colonna PIE + SUNBURST
        dbc.Col([
            dbc.Card([
            dbc.CardHeader(
                dbc.Row([
                    dbc.Col(html.Span("Distribuzione per Classe Selezionata", style=header_style), width="auto"),
                    dbc.Col(
                        dbc.Button("ℹ️ Categorie", id="popover-target2", color="secondary", size="sm", outline=True),
                        width="auto", style={'marginLeft': 'auto'}
                    )
                ], align="center", justify="between", style={'padding': '6px'})
            ),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        # 🔹 STORE + MODALE
                        dcc.Store(id="selected_categoria"),
                        dbc.Modal(
                            [
                                dbc.ModalHeader(dbc.ModalTitle("🔍 Focus Mode - Dettagli Categoria")),
                                dbc.ModalBody(
                                    id="corpo_popup_focus",
                                    style={"whiteSpace": "pre-wrap", "maxHeight": "400px", "overflowY": "auto"}
                                ),
                                dbc.ModalFooter(
                                    dbc.Button("Chiudi", id="chiudi_popup_focus", className="ms-auto", n_clicks=0)
                                ),
                            ],
                            id="popup_focus_mode",
                            is_open=False,
                            size="lg"
                        ),

                        # 🔹 TITOLO (sopra tutto)
                        html.H5("📊 Distribuzione Incubatori per Categoria", style={
                            "textAlign": "center",
                            "marginBottom": "8px",
                            "marginTop": "5px"
                        }),

                        # 🔹 TESTO DINAMICO + ISTRUZIONI
                        html.Div(id="focus_mode_text", style={
                            "marginBottom": "5px",
                            "fontStyle": "italic",
                            "color": "#444",
                            "fontSize": "0.9rem"
                        }),

                        html.P(
                            "ℹ️ Clicca su una fetta per attivare la Focus Mode. Poi usa il pulsante 📋 Dettagli per vedere più info.",
                            style={"color": "#666", "fontSize": "0.85rem", "marginBottom": "10px"}
                        ),

                        # 🔹 PULSANTI — affiancati e uguali
                        html.Div([
                            dbc.Button("📋 Dettagli", id="apri_popup_focus", n_clicks=0, size="sm",
                                    color="info", outline=True, style={"width": "48%"}),
                            dbc.Button("Esci dalla Focus Mode ❌", id="chiudi_focus", n_clicks=0, size="sm",
                                    color="danger", outline=True, style={"width": "48%", "marginLeft": "4%"}),
                        ], style={"display": "flex", "justifyContent": "space-between", "marginBottom": "12px"}),

                        # 🔹 GRAFICO
                        dcc.Graph(
                            id="pie_chart",
                            style={"height": "450px", "width": "100%"},
                            config={"displayModeBar": False}
                        )
                    ], width=6),
                    dbc.Col([
                        html.Div([
                            html.H5("Sunburst Chart per Categoria", style={'textAlign': 'center'}),
                            html.Label("Seleziona dimensione interna:", style={'fontWeight': 'bold', 'marginBottom': '10px'}),

                            dbc.ButtonGroup([
                                dbc.Button("Area Geografica", id="btn-area", n_clicks=0, color="primary", outline=True),
                                dbc.Button("Natura Giuridica", id="btn-natura", n_clicks=0, color="primary", outline=True),
                            ], size="sm", style={"marginBottom": "15px"}),

                            dcc.Store(id="store_sunburst_dimensione", data="area_geografica"),

                            dcc.Graph(
                                id="sunburst_chart",
                                style={"height": "450px", "width": "100%"},
                                config={"displayModeBar": False}
                            )
                        ])
                    ], width=6),
                    # Popover legenda categorie
                    dbc.Popover(
                        id="popover-legenda2",
                        target="popover-target2",
                        body=True,
                        trigger="hover",
                        placement="right",
                        children=html.Div(id="testo_legenda2", style={"whiteSpace": "pre-wrap", "padding": "10px"})
                    )
                ], align="center")
            ], style={'padding': '6px'})
        ], style={"height": "100%"})
    ], width=6)
    ], className="mb-1"),

    # Seconda riga: bar chart con dropdown classi e filtro area
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(
                    dbc.Row([
                        dbc.Col(html.Span("Distribuzione per Classe Selezionata", style=header_style), width="auto"),
                        dbc.Col(
                            dbc.Button("ℹ️ Classi", id="popover-target", color="secondary", size="sm", outline=True),
                            width="auto", style={'marginLeft': 'auto'}
                        )
                    ], align="center", justify="between"), style={'padding': '6px'}
                ),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.Label("Classe:", style={'fontWeight': 'bold', 'marginRight': '8px'}),
                                dcc.Dropdown(
                                    id='classe_dropdown',
                                    options=[
                                        {'label': 'Classe di Produzione', 'value': 'classe di produzione ultimo anno (1)'},
                                        {'label': 'Classe di Addetti', 'value': 'classe di addetti ultimo anno (2)'},
                                        {'label': 'Classe di Capitale', 'value': 'classe di capitale (3)'}
                                    ],
                                    value='classe di produzione ultimo anno (1)',
                                    style={'width': '250px', 'display': 'inline-block'}
                                )
                            ], style={'display': 'flex', 'alignItems': 'center'})
                        ], width="auto"),

                        dbc.Col([
                            html.Div([
                                html.Label("Filtra per area geografica:", style={'fontWeight': 'bold', 'marginRight': '8px'}),
                                dbc.ButtonGroup([
                                    dbc.Button("Nord", id="btn-nord-classe", n_clicks=0),
                                    dbc.Button("Centro", id="btn-centro-classe", n_clicks=0),
                                    dbc.Button("Sud", id="btn-sud-classe", n_clicks=0),
                                    dbc.Button("Tutte", id="btn-tutte-classe", n_clicks=0)
                                ], size="sm")
                            ], style={'display': 'flex', 'alignItems': 'center'})
                        ], width="auto")
                    ], className="mt-3 mb-3", justify="start"),
                    dcc.Store(id="store_area_classe", data="Tutte"),
                    dbc.Popover(
                                    id="popover-legenda",
                                    target="popover-target",
                                    body=True,
                                    children=html.Div(id="testo_legenda"),
                                    trigger="hover",
                                    placement="right",
                                    is_open=False
                                ),
                    html.Div(
                        dcc.Graph(id='bar_chart_classe_generica', style={'height': '450px', 'width': '100%'}),
                        style={'flexGrow': 1}
                    )
                ], style={'padding': '6px', 'height': '100%', 'display': 'flex', 'flexDirection': 'column'})
            ], style={"height": "100%"})
        ], width=6),
        # Quarto Grafico TIMELINE
        dcc.Store(id="store_area_geografica", data="Tutte"),  # <--- AGGIUNGI QUI
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Timeline Cumulativa Iscrizioni / Avvio Attività", style=header_style),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col(html.Div("Filtra per area geografica:", style={'fontWeight': 'bold'}), width="auto"),
                    dbc.Col(
                        dbc.ButtonGroup([
                            dbc.Button("Nord", id="btn-nord", n_clicks=0),
                            dbc.Button("Centro", id="btn-centro", n_clicks=0),
                            dbc.Button("Sud", id="btn-sud", n_clicks=0),
                            dbc.Button("Tutte", id="btn-tutte", n_clicks=0)
                        ], id="area_button_group", size="sm"),
                        width="auto"
                    )
                ], align="center", justify="start", className="mb-2"),

                html.Div(
                    dcc.Graph(id="timeline_cumulativa", style={'height': '450px', 'width': '100%'}),
                    style={'flexGrow': 1}
                )
            ], style={'padding': '6px', 'height': '100%', 'display': 'flex', 'flexDirection': 'column'})
        ], style={"height": "100%"})
        ], width=6, className="mb-1")
    ], className="h-100")
], fluid=True)

# Callback 1: Mappa
@app.callback(
    Output('map_incubatori', 'figure'),
    Output('output_numero_incubatori', 'children'),
    Input('filtro_natgiuridica', 'value')
)
def update_map(natura_sel):
    df_filtrato = df[df['nat.giuridica'] == natura_sel] if natura_sel else df
    df_counts_filtered = df_filtrato.groupby("pv").size().reset_index(name="n_incubatori")
    df_counts_filtered.rename(columns={"pv": "provincia"}, inplace=True)
    df_final = pd.DataFrame({'provincia': province_geojson})
    df_final = df_final.merge(df_counts_filtered, on="provincia", how="left")
    df_final["n_incubatori"] = df_final["n_incubatori"].fillna(0).astype(int)

    fig = px.choropleth(
        df_final,
        geojson=gj_province,
        locations='provincia',
        featureidkey="properties.prov_acr",
        color='n_incubatori',
        color_continuous_scale=["#d9d9d9", "#FFCC00", "#FF9900", "#FF6600", "#FF3300", "#990000"],
        range_color=(0, 11),
        labels={'n_incubatori': 'Numero Incubatori'},
        hover_name='provincia',
        hover_data={'n_incubatori': True, 'provincia': False}
    )

    fig.update_geos(
        projection_type="mercator",
        center={"lat": 42.5, "lon": 12.5},
        projection_scale=5.8,
        visible=False,
        fitbounds="locations"
    )

    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_colorbar=dict(
            title="N° incubatori",
            tickvals=[0, 1, 3, 6, 9, 11],
            ticktext=["Nessuno", "1", "3", "6", "9", "11+"]
        )
    )

    totale = len(df_filtrato)
    testo = f"Numero di {natura_sel.title()}: {totale}" if natura_sel else f"Totale incubatori: {totale}"
    return fig, testo


# Callback secondo grafico
# === Callback Pie Chart ===
@app.callback(
    Output("pie_chart", "figure"),
    Input("selected_categoria", "data")
)
def update_pie_completo(categoria):
    if categoria:
        df_valid = df[df['Categoria'] == categoria]
        titolo = f"Focus: {categoria}"
    else:
        df_valid = df[df['Categoria'].notna()]

    fig = px.pie(
        df_valid,
        names='Categoria',
        color='Categoria',
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig.update_traces(
        textinfo='percent+label',
        textposition='inside',
        insidetextorientation='radial',
        textfont_size=14
    )
    fig.update_layout(margin=dict(t=40, l=0, r=0, b=0), showlegend=False)
    return fig



# === Callback Sunburst ===
# Callback per aggiornare la dimensione selezionata (bottoni toggle)
@app.callback(
    Output("store_sunburst_dimensione", "data"),
    Input("btn-area", "n_clicks"),
    Input("btn-natura", "n_clicks"),
    prevent_initial_call=True
)
def aggiorna_dimensione(n_area, n_natura):
    triggered = ctx.triggered_id
    if triggered == "btn-area":
        return "area_geografica"
    elif triggered == "btn-natura":
        return "nat.giuridica"
    raise PreventUpdate

# Toggle visivo dei pulsanti attivi
@app.callback(
    Output("btn-area", "outline"), Output("btn-natura", "outline"),
    Output("btn-area", "color"), Output("btn-natura", "color"),
    Input("store_sunburst_dimensione", "data")
)
def toggle_attivo(dimensione):
    if dimensione == "area_geografica":
        return False, True, "primary", "secondary"
    else:
        return True, False, "secondary", "primary"

# Unica callback per aggiornare il sunburst_chart
@app.callback(
    Output("sunburst_chart", "figure"),
    Input("store_sunburst_dimensione", "data")
)
def aggiorna_sunburst(dimensione):
    if dimensione not in df.columns:
        raise PreventUpdate

    df_valid = df[df['Categoria'].notna() & df[dimensione].notna()].copy()

    if dimensione == "nat.giuridica":
        acronimi_map = {
            "SOCIETA' A RESPONSABILITA' LIMITATA": "S.R.L",
            "SOCIETA' CONSORTILE A RESPONSABILITA' LIMITATA": "S.C.R.L",
            "SOCIETA' CONSORTILE PER AZIONI": "S.C.P.A",
            "SOCIETA' PER AZIONI": "S.P.A"
        }
        df_valid["dimensione_temp"] = df_valid[dimensione].map(acronimi_map)
    else:
        df_valid["dimensione_temp"] = df_valid[dimensione]

    fig = px.sunburst(
        df_valid,
        path=['dimensione_temp', 'Categoria'],
        color='Categoria',
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig.update_layout(margin=dict(t=40, l=0, r=0, b=0))
    return fig

# Callback Secondo Grafico POPOVER
@app.callback(
    Output("popover-legenda2", "is_open"),
    Input("popover-target2", "n_clicks"),
    State("popover-legenda2", "is_open"),
    prevent_initial_call=True
)
def toggle_popover(n, is_open):
    return not is_open if n else is_open

@app.callback(
    Output("testo_legenda2", "children"),
    Input("popover-target2", "n_clicks"),
    prevent_initial_call=True
)
def mostra_legenda(n):
    return [
        dbc.ListGroupItem("🔹 Multisettoriale – Offrono supporto a startup innovative su vari settori."),
        dbc.ListGroupItem("🔹 Trasferimento tecnologico – supportano startup ad alto contenuto tecnologico."),
        dbc.ListGroupItem("🔹 Regionale – Focus sul territorio/regione e accesso a finanziamenti pubblici."),
        dbc.ListGroupItem("🔹 Universitario – supportano esclusivamente spin‑off " \
        "                     accademici, legati a università e centri di ricerca"),
        dbc.ListGroupItem("🔹 Verticale – Focalizzati su nicchie specifiche"
        "                     (fintech, life sciences, silver economy, energy cleantech)."),
        dbc.ListGroupItem("🔹 Venture builder – Creano nuove startup da zero."),
        dbc.ListGroupItem("🔹 Sostenibilità – Incubano startup con forte orientamento a impatto ambientale," \
        "                     sociale, cultura, economia circolare"),
        dbc.ListGroupItem("🔹 Professionisti / consulenza – Structure legate a grandi network professionali o " \
        "                     corporate, che facilitano innovazione e mentoring"),
    ]

# Callback Secondo Grafico FOCUS MODE

@app.callback(
    Output("selected_categoria", "data"),
    Input("pie_chart", "clickData"),
    prevent_initial_call=True
)
def entra_focus_mode(click_data):
    if click_data:
        return click_data["points"][0]["label"]
    return no_update

@app.callback(
    Output("selected_categoria", "clear_data"),
    Input("chiudi_focus", "n_clicks"),
    prevent_initial_call=True
)
def esci_focus_mode(_):
    return True

@app.callback(
    Output("chiudi_focus", "style"),
    Input("selected_categoria", "data")
)
def mostra_o_nascondi_focus(categoria):
    if categoria:
        return {"marginTop": "-5px", "marginLeft": "auto", "display": "inline-block"}
    return {"marginTop": "-5px", "marginLeft": "auto", "display": "none"}

# Modale

@app.callback(
    Output("popup_focus_mode", "is_open"),
    Input("apri_popup_focus", "n_clicks"),
    Input("chiudi_popup_focus", "n_clicks"),
    State("popup_focus_mode", "is_open"),
    prevent_initial_call=True
)
def toggle_popup(n_apri, n_chiudi, is_open):
    if ctx.triggered_id in ["apri_popup_focus", "chiudi_popup_focus"]:
        return not is_open
    return is_open

@app.callback(
    Output("corpo_popup_focus", "children"),
    Input("selected_categoria", "data")
)
def contenuto_popup(categoria):
    if not categoria:
        return "Nessuna categoria selezionata."

    sottoinsieme = df[df["Categoria"] == categoria]
    n = len(sottoinsieme)
    province = sottoinsieme["pv"].nunique()
    nomi = sottoinsieme["denominazione"].dropna().unique().tolist()

    return f"""\
Categoria selezionata: {categoria}
Totale incubatori: {n}
Province coinvolte: {province}

Elenco incubatori:
- {chr(10).join(nomi)}
"""

 
# Callback terzo grafico
@app.callback(
    Output('bar_chart_classe_generica', 'figure'),
    Input('classe_dropdown', 'value'),
    Input('store_area_classe', 'data')
)
def update_bar_classe(classe_col, area_sel):
    # Filtro area
    if area_sel == "Tutte":
        df_filtrato = df.copy()
    else:
        df_filtrato = df[df['area_geografica'].isin([area_sel])].copy()

    # Pulizia valori
    df_filtrato[classe_col] = df_filtrato[classe_col].astype(str).str.strip().str.upper()
    df_filtrato = df_filtrato[~df_filtrato[classe_col].isin(['', 'NAN', 'NA'])]

    # Gestione classe di capitale (1-11)
    if classe_col == 'classe di capitale (3)':
        df_filtrato['classe_str'] = df_filtrato[classe_col].str.extract(r'(\d+)')[0]
        df_filtrato = df_filtrato[df_filtrato['classe_str'].isin([str(i) for i in range(1, 12)])]
        ordine = [str(i) for i in range(1, 12)]
        df_filtrato['classe'] = pd.Categorical(df_filtrato['classe_str'], categories=ordine, ordered=True)
    else:
        df_filtrato['classe'] = df_filtrato[classe_col]

    # Aggregazione
    dati = (
        df_filtrato
        .groupby('classe', sort=False)
        .agg(
            conteggio=('classe', 'count'),
            incubatori=('denominazione', lambda x: '<br>'.join(x))
        )
        .reset_index()
        .sort_values('classe')
    )

    # Plot
    fig = px.bar(
        dati,
        x='classe',
        y='conteggio',
        text='conteggio',
        labels={'classe': 'Classe', 'conteggio': 'Frequenza'},
        color='classe',
        hover_data={'incubatori': True},
        color_discrete_sequence=px.colors.qualitative.Pastel
    )

    fig.update_layout(
        margin={"r": 0, "t": 30, "l": 0, "b": 0},
        xaxis_title="Classe",
        yaxis_title="Frequenza",
        showlegend=False,
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Arial")
    )

    return fig

# Callback Terzo Grafico Pulsanti

@app.callback(
    Output("store_area_classe", "data"),
    Input("btn-nord-classe", "n_clicks"),
    Input("btn-centro-classe", "n_clicks"),
    Input("btn-sud-classe", "n_clicks"),
    Input("btn-tutte-classe", "n_clicks"),
    prevent_initial_call=True
)
def aggiorna_area_classe(n_nord, n_centro, n_sud, n_tutte):
    triggered = ctx.triggered_id
    if triggered == "btn-nord-classe":
        return "Nord"
    elif triggered == "btn-centro-classe":
        return "Centro"
    elif triggered == "btn-sud-classe":
        return "Sud"
    return "Tutte"

@app.callback(
    Output("btn-nord-classe", "color"), Output("btn-nord-classe", "outline"),
    Output("btn-centro-classe", "color"), Output("btn-centro-classe", "outline"),
    Output("btn-sud-classe", "color"), Output("btn-sud-classe", "outline"),
    Output("btn-tutte-classe", "color"), Output("btn-tutte-classe", "outline"),
    Input("store_area_classe", "data")
)
def toggle_bottone_attivo_classe(area_sel):
    def stile(area):
        return ("primary", False) if area_sel == area else ("primary", True)

    nord_c, nord_o = stile("Nord")
    centro_c, centro_o = stile("Centro")
    sud_c, sud_o = stile("Sud")
    tutte_c, tutte_o = stile("Tutte")

    return nord_c, nord_o, centro_c, centro_o, sud_c, sud_o, tutte_c, tutte_o



# Callback Terzo Grafico POPOVER

@app.callback(
    Output("testo_legenda", "children"),
    Input("classe_dropdown", "value")
)
def update_legenda(classe_selezionata):
    legende = {
        "classe di produzione ultimo anno (1)": html.Div([
            html.H6("📘 Legenda Classe di Produzione"),
            html.Ul([
                html.Li("A: 0 - 100.000 €"),
                html.Li("B: 100.001 - 500.000 €"),
                html.Li("C: 500.001 - 1.000.000 €"),
                html.Li("D: 1.000.001 - 2.000.000 €"),
                html.Li("E: 2.000.001 - 5.000.000 €"),
                html.Li("F: 5.000.001 - 10.000.000 €"),
                html.Li("G: 10.000.001 - 50.000.000 €"),
                html.Li("H: oltre 50.000.000 €")
            ])
        ]),
        "classe di addetti ultimo anno (2)": html.Div([
            html.H6("👥 Legenda Classe di Addetti"),
            html.Ul([
                html.Li("A: 0-4"),
                html.Li("B: 5-9"),
                html.Li("C: 10-19"),
                html.Li("D: 20-49"),
                html.Li("E: 50-249"),
                html.Li("F: 250 e oltre")
            ])
        ]),
        "classe di capitale (3)": html.Div([
            html.H6("💰 Legenda Classe di Capitale"),
            html.Ul([
                html.Li("1: 1 €"),
                html.Li("2: 1 - 5.000 €"),
                html.Li("3: 5.001 - 10.000 €"),
                html.Li("4: 10.001 - 50.000 €"),
                html.Li("5: 50.001 - 100.000 €"),
                html.Li("6: 100.001 - 250.000 €"),
                html.Li("7: 250.001 - 500.000 €"),
                html.Li("8: 500.001 - 1.000.000 €"),
                html.Li("9: 1.000.001 - 2.500.000 €"),
                html.Li("10: 2.500.001 - 5.000.000 €"),
                html.Li("11: oltre 5.000.000 €")
            ])
        ])
    }

    return legende.get(classe_selezionata, "Legenda non disponibile.")

# Callback quarto grafico

# Store area selezionata
@app.callback(
    Output("store_area_geografica", "data"),
    Input("btn-nord", "n_clicks"),
    Input("btn-centro", "n_clicks"),
    Input("btn-sud", "n_clicks"),
    Input("btn-tutte", "n_clicks"),
    prevent_initial_call=True
)
def aggiorna_area(n_nord, n_centro, n_sud, n_tutte):
    triggered = ctx.triggered_id
    if triggered == "btn-nord":
        return "Nord"
    elif triggered == "btn-centro":
        return "Centro"
    elif triggered == "btn-sud":
        return "Sud"
    return "Tutte"


# Toggle visivo pulsanti attivi/inattivi
@app.callback(
    Output("btn-nord", "color"), Output("btn-nord", "outline"),
    Output("btn-centro", "color"), Output("btn-centro", "outline"),
    Output("btn-sud", "color"), Output("btn-sud", "outline"),
    Output("btn-tutte", "color"), Output("btn-tutte", "outline"),
    Input("store_area_geografica", "data")
)
def toggle_bottone_attivo(area_sel):
    def stile(area):
        return ("primary", False) if area_sel == area else ("primary", True)

    nord_c, nord_o = stile("Nord")
    centro_c, centro_o = stile("Centro")
    sud_c, sud_o = stile("Sud")
    tutte_c, tutte_o = stile("Tutte")

    return nord_c, nord_o, centro_c, centro_o, sud_c, sud_o, tutte_c, tutte_o


# Callback del grafico timeline cumulativa
@app.callback(
    Output("timeline_cumulativa", "figure"),
    Input("timeline_cumulativa", "id"),
    Input("store_area_geografica", "data")
)
def aggiorna_timeline(_, area_sel):
    df_dates = df.copy()

    if area_sel != "Tutte" and "area_geografica" in df.columns:
        df_dates = df_dates[df_dates["area_geografica"] == area_sel]

    date_cols = [
        'data iscrizione alla sezione degli incubatori',
        'data iscrizione al Registro Imprese',
        "data inizio dell'esercizio effettivo dell'attività"
    ]
    df_dates[date_cols] = df_dates[date_cols].apply(pd.to_datetime, format="%d/%m/%Y", errors='coerce')

    timeline_df = pd.DataFrame()
    for col in date_cols:
        temp = df_dates[[col]].dropna()
        temp['evento'] = col
        temp['data'] = temp[col]
        timeline_df = pd.concat([timeline_df, temp[['data', 'evento']]])

    timeline_df = (
        timeline_df.groupby(['data', 'evento'])
        .size()
        .reset_index(name='count')
        .sort_values('data')
    )

    timeline_df['cumulato'] = timeline_df.groupby('evento')['count'].cumsum()

    nome_evento = {
        'data iscrizione alla sezione degli incubatori': '📘 Iscrizione Incubatori',
        'data iscrizione al Registro Imprese': '🏛️ Registro Imprese',
        "data inizio dell'esercizio effettivo dell'attività": '🚀 Inizio Attività'
    }
    timeline_df['evento'] = timeline_df['evento'].map(nome_evento)

    fig = px.line(
        timeline_df,
        x='data',
        y='cumulato',
        color='evento',
        markers=True,
        line_shape='spline',
        labels={'data': 'Data', 'cumulato': 'Incubatori Cumulati', 'evento': 'Tipo Evento'},
        title=f'📈 Andamento Cumulativo degli Incubatori - Area: {area_sel}',
        color_discrete_sequence=['#66c2a5', '#fc8d62', '#8da0cb']
    )

    fig.update_traces(marker=dict(size=7), line=dict(width=3))
    fig.update_layout(
        margin={"r": 20, "t": 60, "l": 20, "b": 40},
        hovermode='x unified',
        xaxis_title=None,
        yaxis_title=None,
        yaxis_tickformat=',',
        template='plotly_white',
        legend=dict(
            title='',
            orientation='h',
            yanchor='top',
            y=-0.25,
            xanchor='center',
            x=0.5
        )
    )
    return fig

# === AVVIO IN LOCALE ===
if __name__ == "__main__":
    app.run(debug=True)



