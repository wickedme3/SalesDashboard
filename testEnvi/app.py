import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import dash
from dash import dcc, html, dash_table, Input, Output
import dash_bootstrap_components as dbc

# ── Load & clean data ──────────────────────────────────────────
df = pd.read_csv('asset/data/sales_data.csv')
df['order_date']  = pd.to_datetime(df['order_date'])
df['month_name']  = df['order_date'].dt.strftime('%b %Y')
df['month_order'] = df['order_date'].dt.to_period('M')
df['total_amount'] = df['total_amount'].fillna(df['quantity'] * df['unit_price'])
# ── Chart factory functions ────────────────────────────────────
def make_revenue_trend(d):
    m = (d.groupby(['month_order','month_name'], as_index=False)
          .agg(revenue=('total_amount','sum')).sort_values('month_order'))
    fig = go.Figure(go.Scatter(
        x=m['month_name'], y=m['revenue'],
        mode='lines+markers', fill='tozeroy',
        line=dict(color='#2E75B6', width=3),
        marker=dict(size=8), fillcolor='rgba(46,117,182,0.1)'
    ))
    fig.update_layout(title='Monthly Revenue Trend',
        xaxis_title='Month', yaxis_title='Revenue (PHP)',
        plot_bgcolor='white', hovermode='x unified',
        yaxis=dict(tickformat=',.0f'))
    return fig

def make_category_bar(d):
    b = (d.groupby('category', as_index=False)
          .agg(revenue=('total_amount','sum')).sort_values('revenue'))
    fig = px.bar(b, x='revenue', y='category', orientation='h',
        color='revenue', color_continuous_scale='Blues',
        title='Revenue by Category', text_auto=',.0f',
        labels={'revenue':'Revenue (PHP)','category':''})
    fig.update_layout(coloraxis_showscale=False, plot_bgcolor='white')
    return fig

def make_region_pie(d):
    r = d.groupby('region', as_index=False).agg(revenue=('total_amount','sum'))
    return px.pie(r, names='region', values='revenue', hole=0.4,
        title='Revenue by Region',
        color_discrete_sequence=px.colors.sequential.Blues_r)

def make_top_customers(d):
    t = (d.groupby('customer_name', as_index=False)
          .agg(revenue=('total_amount','sum'))
          .sort_values('revenue', ascending=False).head(10)
          .sort_values('revenue'))
    fig = px.bar(t, x='revenue', y='customer_name', orientation='h',
        color='revenue', color_continuous_scale='Blues',
        title='Top 10 Customers', text_auto=',.0f',
        labels={'revenue':'Total Spend (PHP)','customer_name':''})
    fig.update_layout(coloraxis_showscale=False, plot_bgcolor='white')
    return fig
    
def kpi_card(title, value, icon, color):
    return dbc.Card([dbc.CardBody([
        html.Div([
            html.I(className=f'bi {icon} fs-2', style={'color': color}),
            html.Div([
                html.P(title, className='text-muted mb-0',
                       style={'fontSize':'0.85rem'}),
                html.H4(value, className='mb-0 fw-bold', style={'color': color})
            ], className='ms-3')
        ], className='d-flex align-items-center')
    ])], className='shadow-sm h-100')

# ── App init ───────────────────────────────────────────────────
app = dash.Dash(__name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        'https://cdn.jsdelivr.net/npm/bootstrap-icons/font/bootstrap-icons.css'
    ],
    title='Sales Dashboard')

# ── Layout ─────────────────────────────────────────────────────
app.layout = dbc.Container([
    dbc.Row([dbc.Col(html.H2('Sales Transaction Dashboard',
        className='text-white fw-bold py-3 mb-0'),
        style={'background':'#1F4E79'})], className='mb-4'),
    dbc.Row([
        dbc.Col([html.Label('Region:'), dcc.Dropdown(
            id='region-filter', multi=True, placeholder='All...',
            options=[{'label':r,'value':r} for r in sorted(df.region.unique())])], md=4),
        dbc.Col([html.Label('Category:'), dcc.Dropdown(
            id='category-filter', multi=True, placeholder='All...',
            options=[{'label':c,'value':c} for c in sorted(df.category.unique())])], md=4),
        dbc.Col([html.Label('Dates:'), dcc.DatePickerRange(
            id='date-filter',
            start_date=df.order_date.min(), end_date=df.order_date.max(),
            display_format='MMM DD, YYYY')], md=4),
    ], className='mb-4 p-3 bg-light rounded'),
    dbc.Row(id='kpi-row', className='mb-4'),
    dbc.Row([dbc.Col(dcc.Graph(id='revenue-trend'), md=8),
             dbc.Col(dcc.Graph(id='region-pie'),    md=4)], className='mb-4'),
    dbc.Row([dbc.Col(dcc.Graph(id='category-bar'),  md=6),
             dbc.Col(dcc.Graph(id='top-customers'), md=6)], className='mb-4'),
    dbc.Row([dbc.Col([
        html.H5('Transaction Details', className='fw-bold mb-3'),
        dash_table.DataTable(
            id='data-table', page_size=15,
            sort_action='native', filter_action='native',
            columns=[{'name':c.replace('_',' ').title(),'id':c}
                     for c in ['order_id','order_date','customer_name',
                               'region','category','product_name',
                               'quantity','unit_price','total_amount']],
            style_header={'backgroundColor':'#1F4E79',
                          'color':'white','fontWeight':'bold'},
            style_data_conditional=[{'if':{'row_index':'odd'},
                                     'backgroundColor':'#F0F4F8'}],
            style_cell={'textAlign':'left','padding':'8px',
                        'fontFamily':'Arial','fontSize':'13px'}
        )
    ])])
], fluid=True)

# ── Callback ───────────────────────────────────────────────────
@app.callback(
    Output('kpi-row','children'),      Output('revenue-trend','figure'),
    Output('region-pie','figure'),      Output('category-bar','figure'),
    Output('top-customers','figure'),   Output('data-table','data'),
    Input('region-filter','value'),     Input('category-filter','value'),
    Input('date-filter','start_date'),  Input('date-filter','end_date'),
)
def update_dashboard(regions, categories, start_date, end_date):
    f = df.copy()
    if regions:    f = f[f.region.isin(regions)]
    if categories: f = f[f.category.isin(categories)]
    if start_date: f = f[f.order_date >= start_date]
    if end_date:   f = f[f.order_date <= end_date]

    rev    = f.total_amount.sum()
    orders = len(f)
    kpis = dbc.Row([
        dbc.Col(kpi_card('Total Revenue',   f'PHP {rev:,.0f}',
                         'bi-currency-dollar','#1F4E79'), md=3),
        dbc.Col(kpi_card('Total Orders',    f'{orders:,}',
                         'bi-receipt','#2E75B6'), md=3),
        dbc.Col(kpi_card('Avg Order Value', f'PHP {rev/orders:,.0f}' if orders else 'N/A',
                         'bi-graph-up','#17A2B8'), md=3),
        dbc.Col(kpi_card('Units Sold',      f'{f.quantity.sum():,}',
                         'bi-box-seam','#28A745'), md=3),
    ])
    td = f[['order_id','order_date','customer_name','region',
             'category','product_name','quantity','unit_price',
             'total_amount']].copy()
    td['order_date']   = td.order_date.dt.strftime('%Y-%m-%d')
    td['unit_price']   = td.unit_price.map('{:,.2f}'.format)
    td['total_amount'] = td.total_amount.map('{:,.2f}'.format)
    return kpis, make_revenue_trend(f), make_region_pie(f), \
           make_category_bar(f), make_top_customers(f), td.to_dict('records')

if __name__ == '__main__':
    app.run(debug=True)   # debug=True enables hot reload