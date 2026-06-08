import pandas as pd
import numpy as np
from scipy import stats

import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go

# ─────────────────────────────────────────────
# Leitura e limpeza dos dados
# ─────────────────────────────────────────────
df = pd.read_csv("ecommerce_estatistica.csv", index_col=0)

def parse_qtd(val):
    if isinstance(val, (int, float)):
        return float(val)
    val = str(val).replace("+", "").strip().lower()
    for sufx, fator in [("mil", 1_000), ("k", 1_000), ("m", 1_000_000)]:
        if val.endswith(sufx):
            return float(val.replace(sufx, "")) * fator
    try:
        return float(val)
    except ValueError:
        return np.nan

df["Qtd_Vendidos_num"] = df["Qtd_Vendidos"].apply(parse_qtd)

# ─────────────────────────────────────────────
# Paleta e helpers
# ─────────────────────────────────────────────
PRIMARY  = "#6C63FF"
ACCENT   = "#FF6584"
BG_CARD  = "#FFFFFF"
BG_PAGE  = "#F4F4FB"
TEXT     = "#2D2D3A"

PLOTLY_TEMPLATE = dict(
    layout=dict(
        font=dict(family="Inter, sans-serif", color=TEXT),
        paper_bgcolor=BG_CARD,
        plot_bgcolor=BG_CARD,
        colorway=[PRIMARY, ACCENT, "#48CAE4", "#F4A261", "#2EC4B6", "#FFBE0B"],
        title=dict(font=dict(size=15, color=TEXT)),
        margin=dict(t=50, b=40, l=50, r=20),
        xaxis=dict(showgrid=True, gridcolor="#ECECF6", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#ECECF6", zeroline=False),
    )
)

def card(title, graph_id, md=6):
    return dbc.Col(
        dbc.Card([
            dbc.CardHeader(title, style={
                "fontWeight": "700", "fontSize": "14px",
                "background": "linear-gradient(90deg,#6C63FF 0%,#48CAE4 100%)",
                "color": "#fff", "borderRadius": "12px 12px 0 0"
            }),
            dbc.CardBody(dcc.Graph(id=graph_id, config={"displayModeBar": False}))
        ], style={"borderRadius": "12px", "boxShadow": "0 2px 16px rgba(108,99,255,.12)",
                  "marginBottom": "24px", "border": "none"}),
        md=md, style={"padding": "6px"}
    )

# ─────────────────────────────────────────────
# App
# ─────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap"
    ]
)
app.title = "E-commerce Analytics"

# ─── SIDEBAR ──────────────────────────────────
sidebar = html.Div([
    html.Div([
        html.Span("📊", style={"fontSize": "28px"}),
        html.H5("E-commerce\nAnalytics", style={"color": "#fff", "margin": "0",
                                                  "lineHeight": "1.3", "fontWeight": "700"}),
    ], style={"display": "flex", "alignItems": "center", "gap": "12px",
              "padding": "24px 20px 20px"}),

    html.Hr(style={"borderColor": "rgba(255,255,255,.2)", "margin": "0 20px"}),

    html.P("FILTROS", style={"color": "rgba(255,255,255,.5)", "fontSize": "11px",
                              "letterSpacing": "2px", "padding": "20px 20px 6px",
                              "margin": "0"}),

    html.Div([
        html.Label("Gênero", style={"color": "#fff", "fontSize": "13px", "marginBottom": "6px"}),
        dcc.Dropdown(
            id="filter-genero",
            options=[{"label": "Todos", "value": "Todos"}] +
                    [{"label": g, "value": g} for g in sorted(df["Gênero"].dropna().unique())],
            value="Todos",
            clearable=False,
            style={"fontSize": "13px"}
        )
    ], style={"padding": "0 20px 20px"}),

    html.Div([
        html.Label("Faixa de Preço (R$)", style={"color": "#fff", "fontSize": "13px",
                                                   "marginBottom": "8px"}),
        dcc.RangeSlider(
            id="filter-preco",
            min=int(df["Preço"].min()),
            max=int(df["Preço"].max()),
            step=10,
            value=[int(df["Preço"].min()), int(df["Preço"].max())],
            marks={
                int(df["Preço"].min()): {"label": f"R${int(df['Preço'].min())}",
                                          "style": {"color": "#fff", "fontSize": "11px"}},
                int(df["Preço"].max()): {"label": f"R${int(df['Preço'].max())}",
                                          "style": {"color": "#fff", "fontSize": "11px"}}
            },
            tooltip={"placement": "bottom", "always_visible": False}
        )
    ], style={"padding": "0 20px 20px"}),

    html.Hr(style={"borderColor": "rgba(255,255,255,.2)", "margin": "0 20px"}),

    html.P("MÉTRICAS", style={"color": "rgba(255,255,255,.5)", "fontSize": "11px",
                               "letterSpacing": "2px", "padding": "20px 20px 6px", "margin": "0"}),

    html.Div(id="sidebar-metrics", style={"padding": "0 20px 20px"}),

], style={
    "background": "linear-gradient(180deg, #6C63FF 0%, #3B37B0 100%)",
    "minHeight": "100vh", "width": "260px", "position": "fixed",
    "top": 0, "left": 0, "zIndex": 1000, "overflowY": "auto"
})

# ─── MAIN CONTENT ────────────────────────────
content = html.Div([
    # Header
    html.Div([
        html.H4("Dashboard — Análise de E-commerce",
                style={"margin": "0", "fontWeight": "700", "color": TEXT}),
        html.Span(id="record-count",
                  style={"background": PRIMARY, "color": "#fff", "borderRadius": "20px",
                         "padding": "4px 14px", "fontSize": "13px", "fontWeight": "600"})
    ], style={"display": "flex", "alignItems": "center", "justifyContent": "space-between",
              "background": "#fff", "padding": "16px 28px",
              "boxShadow": "0 1px 8px rgba(0,0,0,.07)", "marginBottom": "24px"}),

    # Gráficos - linha 1
    dbc.Row([
        card("📊 Histograma – Distribuição de Notas",       "fig-histograma",  md=6),
        card("🔵 Dispersão – Preço vs Nota",                "fig-dispersao",   md=6),
    ], style={"margin": "0 8px"}),

    # Gráficos - linha 2
    dbc.Row([
        card("🌡️ Mapa de Calor – Correlações",             "fig-heatmap",     md=7),
        card("🥧 Pizza – Distribuição por Gênero",          "fig-pizza",       md=5),
    ], style={"margin": "0 8px"}),

    # Gráficos - linha 3
    dbc.Row([
        card("📈 Barras – Top 10 Marcas por Vendas",        "fig-barras",      md=12),
    ], style={"margin": "0 8px"}),

    # Gráficos - linha 4
    dbc.Row([
        card("〰️ Densidade – Preço por Gênero",             "fig-densidade",   md=6),
        card("📉 Regressão – Desconto vs Vendas",           "fig-regressao",   md=6),
    ], style={"margin": "0 8px"}),

], style={"marginLeft": "260px", "background": BG_PAGE, "minHeight": "100vh"})

app.layout = html.Div([sidebar, content])

# ─────────────────────────────────────────────
# CALLBACKS
# ─────────────────────────────────────────────
@app.callback(
    Output("sidebar-metrics", "children"),
    Output("record-count", "children"),
    Output("fig-histograma",  "figure"),
    Output("fig-dispersao",   "figure"),
    Output("fig-heatmap",     "figure"),
    Output("fig-pizza",       "figure"),
    Output("fig-barras",      "figure"),
    Output("fig-densidade",   "figure"),
    Output("fig-regressao",   "figure"),
    Input("filter-genero", "value"),
    Input("filter-preco",  "value"),
)
def update_all(genero, preco_range):
    # ── filtro ──────────────────────────────
    dff = df.copy()
    if genero != "Todos":
        dff = dff[dff["Gênero"] == genero]
    dff = dff[(dff["Preço"] >= preco_range[0]) & (dff["Preço"] <= preco_range[1])]

    n = len(dff)

    # ── métricas sidebar ────────────────────
    def metric_badge(label, value):
        return html.Div([
            html.Div(value, style={"color": "#fff", "fontWeight": "700", "fontSize": "22px"}),
            html.Div(label, style={"color": "rgba(255,255,255,.65)", "fontSize": "12px"})
        ], style={"background": "rgba(255,255,255,.12)", "borderRadius": "10px",
                  "padding": "12px 16px", "marginBottom": "10px"})

    metrics = [
        metric_badge("Produtos", f"{n}"),
        metric_badge("Nota Média", f"{dff['Nota'].mean():.2f} ⭐" if n else "—"),
        metric_badge("Preço Médio", f"R$ {dff['Preço'].mean():.0f}" if n else "—"),
        metric_badge("Total Vendas",
                     f"{dff['Qtd_Vendidos_num'].sum()/1000:.0f}k" if n else "—"),
    ]
    record_txt = f"{n} produtos"

    # ── 1. HISTOGRAMA ───────────────────────
    fig_hist = go.Figure(go.Histogram(
        x=dff["Nota"], nbinsx=20,
        marker_color=PRIMARY, opacity=0.85,
        name="Nota"
    ))
    fig_hist.add_vline(x=dff["Nota"].mean(), line_dash="dash", line_color=ACCENT,
                       annotation_text=f"Média {dff['Nota'].mean():.2f}",
                       annotation_position="top right")
    fig_hist.update_layout(PLOTLY_TEMPLATE["layout"],
                           xaxis_title="Nota (estrelas)", yaxis_title="Quantidade")

    # ── 2. DISPERSÃO ────────────────────────
    fig_disp = px.scatter(
        dff, x="Preço", y="Nota", color="Desconto",
        color_continuous_scale="RdYlGn",
        hover_data=["Marca", "Gênero"],
        labels={"Preço": "Preço (R$)", "Nota": "Nota", "Desconto": "Desconto (%)"}
    )
    fig_disp.update_traces(marker=dict(size=7, opacity=0.65))
    fig_disp.update_layout(PLOTLY_TEMPLATE["layout"])

    # ── 3. MAPA DE CALOR ────────────────────
    cols_corr  = ["Nota", "N_Avaliações", "Desconto", "Preço", "Qtd_Vendidos_num"]
    labels_map = ["Nota", "N° Aval.", "Desconto", "Preço", "Qtd. Vendidos"]
    corr = dff[cols_corr].corr().values
    fig_heat = go.Figure(go.Heatmap(
        z=corr, x=labels_map, y=labels_map,
        colorscale="RdYlGn", zmin=-1, zmax=1,
        text=np.round(corr, 2), texttemplate="%{text}",
        hoverongaps=False
    ))
    fig_heat.update_layout(PLOTLY_TEMPLATE["layout"])

    # ── 4. PIZZA ────────────────────────────
    genero_cnt = dff["Gênero"].value_counts().reset_index()
    genero_cnt.columns = ["Gênero", "count"]
    fig_pizza = px.pie(
        genero_cnt, names="Gênero", values="count",
        color_discrete_sequence=[PRIMARY, ACCENT, "#48CAE4", "#F4A261", "#2EC4B6", "#FFBE0B"],
        hole=0.35
    )
    fig_pizza.update_traces(textposition="inside", textinfo="percent+label")
    fig_pizza.update_layout(PLOTLY_TEMPLATE["layout"], showlegend=False)

    # ── 5. BARRAS ────────────────────────────
    top_marcas = (dff.groupby("Marca")["Qtd_Vendidos_num"]
                  .sum().sort_values(ascending=False).head(10).reset_index())
    top_marcas["Marca"] = top_marcas["Marca"].str.title()
    fig_barras = px.bar(
        top_marcas, x="Marca", y="Qtd_Vendidos_num",
        color="Qtd_Vendidos_num", color_continuous_scale=[[0, "#C3C0FF"], [1, PRIMARY]],
        labels={"Qtd_Vendidos_num": "Total Vendido", "Marca": ""},
        text=top_marcas["Qtd_Vendidos_num"].apply(lambda x: f"{x/1000:.0f}k")
    )
    fig_barras.update_traces(textposition="outside")
    fig_barras.update_layout(PLOTLY_TEMPLATE["layout"], coloraxis_showscale=False)

    # ── 6. DENSIDADE ─────────────────────────
    generos_top = dff["Gênero"].value_counts().head(4).index.tolist()
    cores_dens  = [PRIMARY, ACCENT, "#48CAE4", "#F4A261"]
    fig_dens = go.Figure()
    for i, gen in enumerate(generos_top):
        subset = dff[dff["Gênero"] == gen]["Preço"].dropna()
        if len(subset) < 5:
            continue
        kde   = stats.gaussian_kde(subset)
        x_rng = np.linspace(subset.min(), subset.max(), 300)
        y_rng = kde(x_rng)
        fig_dens.add_trace(go.Scatter(
            x=x_rng, y=y_rng, name=gen,
            line=dict(color=cores_dens[i], width=2.5),
            fill="tozeroy", fillcolor=cores_dens[i].replace(")", ", 0.12)").replace("rgb", "rgba")
                                       if "rgb" in cores_dens[i] else cores_dens[i] + "1F"
        ))
    fig_dens.update_layout(PLOTLY_TEMPLATE["layout"],
                           xaxis_title="Preço (R$)", yaxis_title="Densidade")

    # ── 7. REGRESSÃO ─────────────────────────
    df_reg = dff[["Desconto", "Qtd_Vendidos_num"]].dropna()
    fig_reg = go.Figure()
    if len(df_reg) >= 5:
        df_reg = df_reg[df_reg["Qtd_Vendidos_num"] <= df_reg["Qtd_Vendidos_num"].quantile(0.95)]
        slope, intercept, r_val, p_val, _ = stats.linregress(
            df_reg["Desconto"], df_reg["Qtd_Vendidos_num"])
        x_line = np.linspace(df_reg["Desconto"].min(), df_reg["Desconto"].max(), 200)
        y_line = slope * x_line + intercept
        fig_reg.add_trace(go.Scatter(
            x=df_reg["Desconto"], y=df_reg["Qtd_Vendidos_num"],
            mode="markers", name="Produtos",
            marker=dict(color=PRIMARY, size=7, opacity=0.45)
        ))
        fig_reg.add_trace(go.Scatter(
            x=x_line, y=y_line, mode="lines",
            name=f"Regressão  R²={r_val**2:.3f}  p={p_val:.3f}",
            line=dict(color=ACCENT, width=2.5)
        ))
    fig_reg.update_layout(PLOTLY_TEMPLATE["layout"],
                          xaxis_title="Desconto (%)", yaxis_title="Quantidade Vendida")

    return metrics, record_txt, fig_hist, fig_disp, fig_heat, fig_pizza, fig_barras, fig_dens, fig_reg


# ─────────────────────────────────────────────
server = app.server  # necessário para o gunicorn no deploy

if __name__ == "__main__":
    app.run(debug=False)
