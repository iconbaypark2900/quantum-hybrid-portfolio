"""
Quantum Hybrid Portfolio Dashboard
Interactive visualization for quantum-inspired portfolio optimization
"""
import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
import numpy as np
import pandas as pd
import networkx as nx
from datetime import datetime, timedelta

# Import quantum hybrid portfolio modules
from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer, QSWResult
from core.quantum_inspired.graph_builder import FinancialGraphBuilder
from config.qsw_config import QSWConfig

# Initialize the app
app = dash.Dash(__name__, title="Quantum Hybrid Portfolio Dashboard")
server = app.server

# Mock data generator for demonstration
def generate_mock_portfolio_data():
    """Generate mock portfolio data for demonstration."""
    n_assets = 10
    assets = [f'ASSET_{i}' for i in range(1, n_assets + 1)]
    
    # Mock returns, volatility, and weights
    returns = np.random.uniform(0.05, 0.15, n_assets)  # 5% to 15% returns
    volatility = np.random.uniform(0.15, 0.30, n_assets)  # 15% to 30% volatility
    weights = np.random.dirichlet([1.0] * n_assets)  # Dirichlet for normalized weights
    
    # Calculate Sharpe ratio
    sharpe_ratios = returns / volatility
    
    return {
        'assets': assets,
        'returns': returns,
        'volatility': volatility,
        'weights': weights,
        'sharpe_ratios': sharpe_ratios,
        'overall_metrics': {
            'sharpe': np.mean(sharpe_ratios),
            'return': np.mean(returns),
            'volatility': np.mean(volatility),
            'turnover': np.random.uniform(0.05, 0.15),
            'n_assets': n_assets
        }
    }

# High-contrast layout styles so text and buttons are visible
COMMON_LABEL_STYLE = {'color': '#1a1a1a', 'fontSize': '14px', 'fontWeight': '600', 'display': 'block', 'marginBottom': '4px'}
COMMON_SURFACE = {'backgroundColor': '#f5f5f5', 'color': '#1a1a1a'}

# Layout definition
app.layout = html.Div([
    html.H1("🌌 Quantum Hybrid Portfolio Dashboard", 
             style={'textAlign': 'center', 'marginBottom': 30, 'color': '#1a1a1a'}),
    
    html.Div([
        # Control Panel
        html.Div([
            html.H3("Configuration", style={'color': '#1a1a1a'}),
            
            html.Label("Number of Assets:", style=COMMON_LABEL_STYLE),
            dcc.Slider(id='n-assets-slider', min=5, max=30, value=10, step=1),
            
            html.Br(),
            html.Label("Market Regime:", style=COMMON_LABEL_STYLE),
            dcc.Dropdown(
                id='market-regime-dropdown',
                options=[
                    {'label': 'Bull Market', 'value': 'bull'},
                    {'label': 'Bear Market', 'value': 'bear'},
                    {'label': 'Volatile', 'value': 'volatile'},
                    {'label': 'Normal', 'value': 'normal'}
                ],
                value='normal'
            ),
            
            html.Br(),
            html.Label("Omega Parameter (Mixing):", style=COMMON_LABEL_STYLE),
            dcc.Slider(id='omega-slider', min=0.1, max=0.5, value=0.3, step=0.05),
            
            html.Br(),
            html.Button('Run Optimization', id='run-btn', n_clicks=0,
                       style={'width': '100%', 'padding': '10px', 'fontSize': '16px', 'backgroundColor': '#2563eb', 'color': '#fff', 'border': 'none', 'borderRadius': '6px', 'cursor': 'pointer', 'fontWeight': '600'}),
            
            html.Div(id='optimization-status', style={'marginTop': '8px', 'color': '#1a1a1a', 'fontSize': '13px'}),
            
        ], style={'width': '20%', 'display': 'inline-block', 'verticalAlign': 'top', 
                  'padding': '20px', 'borderRight': '1px solid #ccc', **COMMON_SURFACE}),
        
        # Main Results Panel
        html.Div([
            # Key Metrics Cards
            html.Div([
                html.Div([
                    html.H4("Sharpe Ratio", style={'color': '#1a1a1a', 'margin': '0 0 8px 0'}),
                    html.H2(id="sharpe-value", children="0.00", style={'color': '#1a1a1a', 'margin': 0})
                ], className="metric-card", style={
                    'width': '23%', 'display': 'inline-block', 'text-align': 'center',
                    'backgroundColor': '#e5e7eb', 'padding': '20px', 'margin': '10px',
                    'borderRadius': '10px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)', 'color': '#1a1a1a'
                }),
                
                html.Div([
                    html.H4("Expected Return", style={'color': '#1a1a1a', 'margin': '0 0 8px 0'}),
                    html.H2(id="return-value", children="0.00%", style={'color': '#1a1a1a', 'margin': 0})
                ], className="metric-card", style={
                    'width': '23%', 'display': 'inline-block', 'text-align': 'center',
                    'backgroundColor': '#e5e7eb', 'padding': '20px', 'margin': '10px',
                    'borderRadius': '10px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)', 'color': '#1a1a1a'
                }),
                
                html.Div([
                    html.H4("Risk (Volatility)", style={'color': '#1a1a1a', 'margin': '0 0 8px 0'}),
                    html.H2(id="volatility-value", children="0.00%", style={'color': '#1a1a1a', 'margin': 0})
                ], className="metric-card", style={
                    'width': '23%', 'display': 'inline-block', 'text-align': 'center',
                    'backgroundColor': '#e5e7eb', 'padding': '20px', 'margin': '10px',
                    'borderRadius': '10px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)', 'color': '#1a1a1a'
                }),
                
                html.Div([
                    html.H4("Turnover", style={'color': '#1a1a1a', 'margin': '0 0 8px 0'}),
                    html.H2(id="turnover-value", children="0.00%", style={'color': '#1a1a1a', 'margin': 0})
                ], className="metric-card", style={
                    'width': '23%', 'display': 'inline-block', 'text-align': 'center',
                    'backgroundColor': '#e5e7eb', 'padding': '20px', 'margin': '10px',
                    'borderRadius': '10px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)', 'color': '#1a1a1a'
                }),
            ]),
            
            # Charts Row 1
            html.Div([
                html.Div([
                    dcc.Graph(id='allocation-chart', figure={'layout': {'height': 400}})
                ], style={'width': '50%', 'display': 'inline-block'}),
                
                html.Div([
                    dcc.Graph(id='performance-chart', figure={'layout': {'height': 400}})
                ], style={'width': '50%', 'display': 'inline-block'}),
            ], style={'width': '100%'}),
            
            # Charts Row 2
            html.Div([
                html.Div([
                    dcc.Graph(id='risk-return-chart', figure={'layout': {'height': 400}})
                ], style={'width': '50%', 'display': 'inline-block'}),
                
                html.Div([
                    dcc.Graph(id='graph-visualization', figure={'layout': {'height': 400}})
                ], style={'width': '50%', 'display': 'inline-block'}),
            ], style={'width': '100%'}),
            
        ], style={'width': '75%', 'display': 'inline-block', 'verticalAlign': 'top', 
                  'padding': '20px', 'backgroundColor': '#f5f5f5', 'color': '#1a1a1a'}),
    ]),
    
    # Detailed Results Section
    html.Div([
        html.H3("Portfolio Details", style={'color': '#1a1a1a'}),
        html.Div(id='portfolio-details', children=[])
    ], style={'padding': '20px', 'marginTop': '20px', 'borderTop': '1px solid #ccc', 'backgroundColor': '#f5f5f5', 'color': '#1a1a1a'})
], style={'backgroundColor': '#f5f5f5', 'color': '#1a1a1a', 'minHeight': '100vh'})

@app.callback(
    [Output('sharpe-value', 'children'),
     Output('return-value', 'children'),
     Output('volatility-value', 'children'),
     Output('turnover-value', 'children'),
     Output('allocation-chart', 'figure'),
     Output('performance-chart', 'figure'),
     Output('risk-return-chart', 'figure'),
     Output('graph-visualization', 'figure'),
     Output('portfolio-details', 'children'),
     Output('optimization-status', 'children')],
    [Input('run-btn', 'n_clicks')],
    [State('n-assets-slider', 'value'),
     State('market-regime-dropdown', 'value'),
     State('omega-slider', 'value')])
def update_dashboard(n_clicks, n_assets, market_regime, omega):
    """Update dashboard with new optimization results."""
    if n_clicks == 0:
        # Initial load with mock data
        data = generate_mock_portfolio_data()
        status = "Dashboard loaded. Click 'Run Optimization' to start."
    else:
        status = "Running optimization..."
        # Simulate quantum optimization
        try:
            # Create mock returns and covariance
            np.random.seed(42 + n_clicks)  # For consistent results per simulation
            returns = np.random.uniform(0.05, 0.15, n_assets)
            A = np.random.randn(n_assets, n_assets)
            covariance = np.dot(A.T, A) / n_assets
            
            # Create custom config with selected omega
            config = QSWConfig(default_omega=omega)
            optimizer = QuantumStochasticWalkOptimizer(config)
            
            # Run optimization
            result = optimizer.optimize(returns, covariance, market_regime=market_regime)
            
            # Format data for dashboard
            assets = [f'ASSET_{i+1}' for i in range(n_assets)]
            data = {
                'assets': assets,
                'returns': result.expected_return * np.ones(n_assets),  # Simulated individual returns
                'volatility': np.sqrt(np.diag(covariance)),  # Individual volatilities
                'weights': result.weights,
                'sharpe_ratios': returns / np.sqrt(np.diag(covariance)),
                'overall_metrics': {
                    'sharpe': result.sharpe_ratio,
                    'return': result.expected_return,
                    'volatility': result.volatility,
                    'turnover': result.turnover,
                    'n_assets': len(result.weights)
                }
            }
            
            status = f"Optimization completed! Sharpe Ratio: {result.sharpe_ratio:.3f}"
        except Exception as e:
            # Fallback to mock data if actual optimization fails
            data = generate_mock_portfolio_data()
            status = f"Error in optimization: {str(e)}. Showing mock data."

    # Create allocation chart (pie chart of weights)
    allocation_fig = go.Figure(data=[go.Pie(
        labels=data['assets'][:min(10, len(data['assets']))],  # Limit to 10 for readability
        values=data['weights'][:min(10, len(data['weights']))] * 100,
        hovertemplate='<b>%{label}</b><br>' +
                     'Weight: %{value:.2f}%<br>' +
                     '<extra></extra>'
    )])
    allocation_fig.update_layout(
        title='Portfolio Allocation', height=400,
        paper_bgcolor='#f5f5f5', plot_bgcolor='#f5f5f5',
        font=dict(color='#1a1a1a', size=12),
        title_font=dict(size=14, color='#1a1a1a')
    )

    # Create performance chart (bar chart of returns)
    performance_fig = go.Figure(data=[
        go.Bar(x=data['assets'], y=data['returns']*100,
               name='Expected Return %',
               marker_color='skyblue')
    ])
    performance_fig.update_layout(
        title='Expected Returns by Asset',
        xaxis_title='Assets',
        yaxis_title='Expected Return (%)',
        height=400,
        paper_bgcolor='#f5f5f5', plot_bgcolor='#f5f5f5',
        font=dict(color='#1a1a1a', size=12),
        title_font=dict(size=14, color='#1a1a1a')
    )

    # Create risk-return scatter plot
    risk_return_fig = go.Figure(data=go.Scatter(
        x=data['volatility']*100,
        y=data['returns']*100,
        mode='markers+text',
        marker=dict(
            size=20*(data['weights']+0.01)*100,
            sizemode='diameter',
            color=data['sharpe_ratios'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Sharpe Ratio")
        ),
        text=data['assets'],
        textposition="middle center",
        hovertemplate='<b>%{text}</b><br>' +
                     'Risk: %{x:.2f}%<br>' +
                     'Return: %{y:.2f}%<br>' +
                     'Sharpe: %{marker.color:.2f}<br>' +
                     '<extra></extra>'
    ))
    risk_return_fig.update_layout(
        title='Risk vs Return Scatter Plot',
        xaxis_title='Risk (Volatility %)',
        yaxis_title='Expected Return %',
        height=400,
        paper_bgcolor='#f5f5f5', plot_bgcolor='#f5f5f5',
        font=dict(color='#1a1a1a', size=12),
        title_font=dict(size=14, color='#1a1a1a')
    )

    # Create simplified graph visualization
    G = nx.erdos_renyi_graph(n=min(15, len(data['assets'])), p=0.3)
    pos = nx.spring_layout(G, seed=42)
    
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=0.5, color='#888'), 
                           hoverinfo='none', mode='lines')

    node_x = []
    node_y = []
    node_text = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        if node < len(data['assets']):
            node_text.append(f"{data['assets'][node]}<br>{data['weights'][node]*100:.1f}%")
        else:
            node_text.append(f"Asset {node}")

    node_trace = go.Scatter(x=node_x, y=node_y, mode='markers+text', 
                           hoverinfo='text',
                           text=node_text,
                           textposition="middle center",
                           marker=dict(size=20, color=data['sharpe_ratios'][:len(G.nodes())],
                                     colorscale='Viridis', 
                                     colorbar=dict(title="Sharpe Ratio"),
                                     line=dict(width=2, color='white')),
                           textfont=dict(size=10))

    graph_fig = go.Figure(data=[edge_trace, node_trace])
    graph_fig.update_layout(
        title='Network Visualization of Asset Relationships',
        showlegend=False,
        hovermode='closest',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=400,
        paper_bgcolor='#f5f5f5', plot_bgcolor='#f5f5f5',
        font=dict(color='#1a1a1a', size=12),
        title_font=dict(size=14, color='#1a1a1a')
    )

    # Create portfolio details table
    detailed_data = pd.DataFrame({
        'Asset': data['assets'][:10],  # Show top 10
        'Weight %': (data['weights'][:10] * 100).round(2),
        'Expected Return %': (data['returns'][:10] * 100).round(2),
        'Risk %': (data['volatility'][:10] * 100).round(2),
        'Sharpe': data['sharpe_ratios'][:10].round(3)
    })
    
    portfolio_details_table = html.Table([
        html.Thead([
            html.Tr([html.Th(col, style={'color': '#1a1a1a', 'padding': '8px', 'textAlign': 'left', 'borderBottom': '2px solid #1a1a1a'}) for col in detailed_data.columns])
        ]),
        html.Tbody([
            html.Tr([
                html.Td(detailed_data.iloc[i][col], style={'color': '#1a1a1a', 'padding': '8px', 'borderBottom': '1px solid #ccc'}) for col in detailed_data.columns
            ]) for i in range(len(detailed_data))
        ])
    ], style={
        'width': '100%',
        'borderCollapse': 'collapse',
        'marginTop': '10px'
    })

    # Return all updated elements
    return [
        f"{data['overall_metrics']['sharpe']:.3f}",
        f"{data['overall_metrics']['return']*100:.2f}%",
        f"{data['overall_metrics']['volatility']*100:.2f}%",
        f"{data['overall_metrics']['turnover']*100:.2f}%",
        allocation_fig,
        performance_fig,
        risk_return_fig,
        graph_fig,
        portfolio_details_table,
        status
    ]

# Run the app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8050)