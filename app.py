import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
# import dash_renderer as drr
import numpy as np
import pandas as pd
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from os.path import join
import plotly_express as px
import flask
import time

GITHUB_LOGO = 'GitHub-Mark-120px-plus.png'

datapath = './Data'
dimensions = ['x', 'y', 'Color']
dim_info = [
    'The nuclear property to plot on the horizontal axis',
    'The nuclear property to plot on the vertical axis',
    '(Optional) The nuclear property to use for the color bar. '
    'Useful for finding relationships between more than two variables.'
]

massexp = pd.read_excel(join(datapath, 'Mass_Explorer', 'All_Nuclei.xlsx'),
                        sheet_name=None, na_values='No_Data', )
massexp_names = ['Mass Explorer: ' + name.replace('_all_nuclei', '') for name in massexp]
massexp = {name: df for name, df in zip(massexp_names, massexp.values())}

data_sources = ['AME 16 Mass', 'AME 16 React', 'FRDM 2012', *massexp_names]
element_column = {'AME 16 Mass': 'EL', 'AME 16 React': 'elt', 'FRDM 2012': 'EL',
                  **{name: 'Symbol' for name in massexp_names}}

data_defaults = {
    'AME 16 Mass': {'x': 'Beta-Decay Energy', 'y': 'Mass Excess', 'Color': 'Atomic Mass'},
    'AME 16 React': {'x': 'S(2n)', 'y': 'S(2p)', 'Color': 'Q(a)'},
    'FRDM 2012': {'x': 'Emic', 'y': 'Es+p', 'Color': 'Ebind'},
    **{name: {'x': 'S_p_(MeV)', 'y': 'S_n_(MeV)', 'Color': 'Q_{alpha}_(MeV)'} for name in massexp_names}
}

nuclear_chart_color_defaults = {
    'AME 16 Mass': 'Mass Excess',
    'AME 16 React': 'S(p)',
    'FRDM 2012': 'eps4',
    **{name: 'S_p_(MeV)' for name in massexp_names}
}


data_paths = {
    'AME 16 Mass': join(datapath, 'AME2016', 'mass16.csv'),
    'AME 16 React': join(datapath, 'AME2016', 'react16.csv'),
    'FRDM 2012': join(datapath, 'frdm2012named.csv')
}
dfs = {name: pd.read_csv(path) for name, path in data_paths.items()}

dfs = {**dfs, **massexp}
# print(dfs)

colormap = px.colors.diverging.Spectral[::-1]

# external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
external_stylesheets = [dbc.themes.BOOTSTRAP]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.css.append_css({
    'external_url': 'https://use.fontawesome.com/releases/v5.8.1/css/all.css'})
server = app.server

nav_bar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink(html.Img(src=app.get_asset_url(GITHUB_LOGO), height="25px"), href='#')),
        dbc.NavItem(dbc.NavLink('About', href="/")),
        dbc.NavItem(dbc.NavLink('Explore', href="/explore"))
    ],
    brand='Learning Structure in Atomic Nuclei',
    brand_href='/',
    sticky="top",
)

url_bar_and_content_div = html.Div([
    dcc.Location(id='url', pathname='/', refresh=False),
    nav_bar,
    html.Div(id='page-content')
    ],
    style={'margin': 'auto', 'float': 'center', 'display': 'block'}
)


layout_index = html.Div([
    dcc.Markdown("""
        # Welcome

        This app allows you to visually explore the nuclear properties of modern datasets.
        Click on the *Explore* button in the navigation bar or click below to get started.
        """.replace('  ', ''), className='container',
    ),
    html.Div([dbc.Nav([dbc.NavLink("Get Started!", active=True, href="/explore")],
                      pills=True, horizontal='center')],
             style={'padding': '10px'}),
    html.Br(),
    dbc.Alert("This site is under construction! Stay tuned for updates.", color='danger',
              style={'margin': 'auto', 'display': 'table'}),
    html.Br(),
    dcc.Markdown("""
    ## Data
    
    You can explore multiple data sets, including both theoretical predictions and experimental measurements,
    using a simple dropdown menu.
    
    * [AME 2016](https://doi.org/10.1088%2F1674-1137%2F41%2F3%2F030002): The atomic mass evaluation, both the mass and reaction tables.
    * [FRDM 2012](http://www.sciencedirect.com/science/article/pii/S0092640X1600005X): The finite range drop model.
    * [Mass Explorer](http://massexplorer.frib.msu.edu): The DFT mass tables.
    
    ## Credit

    This interactive website was built by Jordan Melendez using Python, Dash and Plotly.
    You can contact him at melendez.27 (at) osu.edu.
    """.replace('  ', ''), className='container',)
], style={'padding': '10px', 'maxWidth': '800px', 'float': 'center',
          'display': 'block', 'margin': 'auto'}
)

layout_graphs = html.Div([
    # dcc.Store(id='memory'),
    dbc.CardDeck(
    [
        dbc.Card(
            [
                dbc.CardHeader(id='nuclides-card', children=[
                    'Chart of Nuclides',
                ]),
                dbc.CardBody(
                    [
                        dbc.CardText("""
                        This chart is interactive!
                        Click and drag over a region of the chart to zoom in.
                        Double click to zoom out. Hover over the chart and click
                        the vertical modebar tools for more options.
                        To plot different nuclear properties as colors, use the
                        dropdown below.
                        """),
                        html.Div([
                            html.Div([
                                'Color:  ',
                                html.I(className='fas fa-question-circle', id='nchart-color-tooltip'),
                                dbc.Tooltip('(Optional) The property used to color each nuclide.',
                                            target='nchart-color-tooltip'),
                                dcc.Dropdown(id='nchart_color', clearable=True),
                            ], style={'width': '50%', 'display': 'inline-block', 'padding': '5px',
                                      'minWidth': '200px'}),

                            html.Div([
                                'Data:  ',
                                html.I(className='fas fa-question-circle', id='nchart-df-tooltip'),
                                dbc.Tooltip('The data set to explore. Applies to all charts.',
                                            target='nchart-df-tooltip'),
                                dcc.Dropdown(id='nchart_df', options=[dict(label=s, value=s) for s in data_sources],
                                             clearable=False, value=data_sources[0])
                            ], style={'width': '50%', 'display': 'inline-block', 'padding': '5px',
                                      'minWidth': '200px'})
                        ],
                        )
                    ]
                ),
            ]
        ),
        dbc.Card(
            [
                dbc.CardHeader('Scatter Plot'),
                dbc.CardBody(
                    [
                        dbc.CardText("""
                        Plot different nuclear properties against one another.
                        Find interesting patterns by changing the x and y axes and color options.
                        Click and drag to select data, which will highlight the corresponding points
                        on the chart of nuclides.
                        """),
                        *[
                            html.Div([
                                d + ':  ',
                                html.I(className='fas fa-question-circle', id=d + '-tooltip'),
                                dbc.Tooltip(info, target=d + '-tooltip'),
                                dcc.Dropdown(id=d, clearable=d == 'Color')
                            ],
                                style={'width': '33%', 'display': 'inline-block', 'padding': '5px',
                                       'minWidth': '200px'})
                            for d, info in zip(dimensions, dim_info)
                        ]
                    ]
                )
            ],
        )
    ], style={'width': '94%', 'float': 'center', 'margin': 'auto'}),
    html.Div(id='graph-div', children=[
        dcc.Graph(
            id='nuclear_chart',
            style={"width": "50%", "display": 'inline-block', 'maxWidth': '1200px',
                   'float': 'center', 'margin': 'auto'}
        ),
        dcc.Graph(id='scatter', style={"width": "50%", "display": "inline-block", 'float': 'right'}),
    ]),
    html.Div([dcc.Loading(html.Div(id='isloading', style={'padding': '0px', 'height': '1px'}), type='dot',
                          style={'display': 'block', 'margin': 'auto', 'float': 'center'})])
], style={'padding': '10px', 'maxWidth': '1600px', 'float': 'center',
          'display': 'block', 'margin': 'auto'})


def serve_layout():
    if flask.has_request_context():
        return url_bar_and_content_div
    return html.Div([
        url_bar_and_content_div,
        layout_graphs,
        layout_index,
    ])


app.layout = serve_layout


@app.callback(Output('isloading', 'children'),
              [Input('nchart_df', 'value')])
def test_div_loading(value):
    time.sleep(2)
    return ['']


# Update the index
@app.callback(dash.dependencies.Output('page-content', 'children'),
              [dash.dependencies.Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/':
        return layout_index
    elif pathname == '/explore':
        return layout_graphs
    else:
        return layout_index
    # You could also return a 404 "URL not found" page here


# @app.callback(Output('memory', 'data'),
#               [Input('nchart_df', 'value')])
# def select_data(data_source):
#     df = pd.read_csv(data_paths[data_source])
#     return df.to_dict()

def clean_up_name(name):
    return name.replace('Beta', 'β').replace('Experimental', 'Exp.')


@app.callback(Output('nchart_color', 'options'),
              [Input('nchart_df', 'value')])
def on_data_set_nuclear_chart_colors(value):
    # options = list(data.keys())
    options = dfs[value].columns
    clean_options = [clean_up_name(name) for name in options]
    return [{'label': clean_name, 'value': name} for clean_name, name in zip(clean_options, options)]


@app.callback(Output('nchart_color', 'value'),
              [Input('nchart_color', 'options')],
              [State('nchart_df', 'value')])
def on_data_set_nuclear_chart_color_default(options, data_source):
    return nuclear_chart_color_defaults[data_source]


for d in dimensions:
    @app.callback(Output(d, 'options'),
                  [Input('nchart_df', 'value')])
    def on_data_set_dropdown_options(value):
        # options = list(data.keys())
        options = dfs[value]
        clean_options = [clean_up_name(name) for name in options]
        return [{'label': clean_name, 'value': name} for clean_name, name in zip(clean_options, options)]


    @app.callback(Output(d, 'value'),
                  [Input('nchart_df', 'value')],
                  [State(d, 'id')])
    def on_data_set_dropdown_value(data_source, dropdown):
        return data_defaults[data_source][dropdown]


def make_rectangle(x0, y0, x1, y1, xref='x', yref='y'):
    return dict(
        type='rect',
        xref=xref,
        yref=yref,
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        opacity=0.2,
        line={
            'color': 'gray',
            'width': 2,
        },
        # layer='below',
        fillcolor='white',
    )


@app.callback(
    Output('nuclear_chart', 'figure'),
    [Input('scatter', 'selectedData'), Input('nchart_color', 'value'), Input('nchart_df', 'value')])
def make_nuclear_chart(selected_data, color, data_source):
    if selected_data is None:
        selected_data = {'points': [None]}

    # df = pd.DataFrame.from_dict(data)
    df = dfs[data_source]
    selected_points = df.index
    selected_index = [p['customdata'] for p in selected_data['points'] if p is not None]
    if len(selected_index) > 0:
        selected_points = np.intersect1d(
            selected_points, selected_index)

    fig = px.scatter(
        df, x='N', y='Z', color=color, hover_name=element_column[data_source],
        symbol_sequence=['square'],
        color_continuous_scale=colormap,
        height=600,
        labels={'Z': 'Proton Number (Z)', 'N': 'Neutron Number (N)'},
        render_mode='webgl'
    )

    magic_nums = [2, 8, 20, 28, 50, 82, 126, 184]
    magic_p = [make_rectangle(df[df['Z'] == p]['N'].min()-4, p-0.5, df[df['Z'] == p]['N'].max()+4, p+0.5)
               for p in magic_nums[:-1] if len(df[df['Z'] == p]['N']) != 0]
    magic_n = [make_rectangle(n-0.5, df[df['N'] == n]['Z'].min()-3, n+0.5, df[df['N'] == n]['Z'].max()+3)
               for n in magic_nums if len(df[df['N'] == n]['Z']) != 0]
    # Increase right margin and make modebar vertical due to problems with drop-downs interfering
    # with the modebar.
    fig.update(data=[dict(selectedpoints=selected_points)],
               layout=dict(margin={'t': 20, 'b': 0, 'r': 160}, modebar=dict(orientation='v'),
                           shapes=[*magic_p, *magic_n])
               )
    return fig


@app.callback(Output('scatter', 'figure'),
              [Input(d, 'value') for d in dimensions] + [Input('nchart_df', 'value')]
              )
def make_scatter(x, y, color, data_source):
    # df = pd.DataFrame.from_dict(data)
    df = dfs[data_source]
    fig = px.scatter(
        df, x=x, y=y, color=color, height=600, hover_name=element_column[data_source],
        color_continuous_scale=colormap,
        render_mode='webgl'  # For speed with many datapoints
    )
    fig.update(data=[dict(customdata=df.index)],
               layout=dict(margin={'t': 20, 'b': 0, 'r': 160}, dragmode='select',
                           modebar=dict(orientation='v')))
    return fig


if __name__ == '__main__':
    app.run_server(debug=True)
