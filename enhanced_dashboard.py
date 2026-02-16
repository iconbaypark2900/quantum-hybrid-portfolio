"""
Enhanced Quantum Hybrid Portfolio Dashboard
Advanced interactive visualization for quantum-inspired portfolio optimization
"""
import dash
from dash import dcc, html, Input, Output, State, ALL
import plotly.graph_objs as go
import plotly.express as px
import numpy as np
import pandas as pd
import networkx as nx
from datetime import datetime, timedelta
import os

# Import quantum hybrid portfolio modules
from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer
from core.quantum_inspired.enhanced_quantum_walk import EnhancedQuantumStochasticWalkOptimizer
from core.quantum_inspired.quantum_annealing import QuantumAnnealingOptimizer
from config.qsw_config import QSWConfig
from enhanced_visualizations import (
    create_correlation_heatmap,
    create_risk_return_scatter,
    create_portfolio_allocation_donut,
    create_sector_allocation_bar,
    create_performance_benchmark_comparison,
    create_time_series_performance,
    create_factor_risk_decomposition,
    create_portfolio_turnover_analysis,
    create_monte_carlo_simulation
)

# Initialize the app
app = dash.Dash(__name__, title="Enhanced Quantum Hybrid Portfolio Dashboard")
server = app.server

# Mock data generator for demonstration
def generate_mock_portfolio_data():
    """Generate mock portfolio data for demonstration."""
    n_assets = 10
    assets = [f'ASSET_{i}' for i in range(1, n_assets + 1)]
    sectors = ['Tech', 'Finance', 'Healthcare', 'Consumer', 'Energy', 'Tech', 'Finance', 'Healthcare', 'Consumer', 'Energy']

    # Mock returns, volatility, and weights
    returns = np.random.uniform(0.05, 0.15, n_assets)  # 5% to 15% returns
    volatility = np.random.uniform(0.15, 0.30, n_assets)  # 15% to 30% volatility
    weights = np.random.dirichlet([1.0] * n_assets)  # Dirichlet for normalized weights

    # Calculate Sharpe ratio
    sharpe_ratios = returns / volatility

    # Create correlation matrix
    A = np.random.randn(n_assets, n_assets)
    correlation_matrix = np.dot(A.T, A) / n_assets
    # Ensure diagonal is 1
    np.fill_diagonal(correlation_matrix, 1.0)

    return {
        'assets': assets,
        'sectors': sectors,
        'returns': returns,
        'volatility': volatility,
        'weights': weights,
        'sharpe_ratios': sharpe_ratios,
        'correlation_matrix': correlation_matrix,
        'overall_metrics': {
            'sharpe': np.mean(sharpe_ratios),
            'return': np.mean(returns),
            'volatility': np.mean(volatility),
            'turnover': np.random.uniform(0.05, 0.15),
            'n_assets': n_assets,
            'diversification_ratio': 0.75,
            'information_ratio': 0.85,
            'max_drawdown': 0.12,
            'alpha': 0.03,
            'beta': 0.95
        }
    }

# High-contrast layout styles so text and buttons are visible
COMMON_LABEL_STYLE = {'color': '#1a1a1a', 'fontSize': '14px', 'fontWeight': '600', 'display': 'block', 'marginBottom': '4px'}
COMMON_SURFACE = {'backgroundColor': '#f5f5f5', 'color': '#1a1a1a'}

# Enhanced theme options
THEMES = {
    'default': {
        'primary': '#2563eb',
        'secondary': '#1e40af',
        'background': '#f5f5f5',
        'surface': '#ffffff',
        'text': '#1a1a1a',
        'accent': '#3b82f6'
    },
    'ocean': {
        'primary': '#0ea5e9',
        'secondary': '#0284c7',
        'background': '#e0f2fe',
        'surface': '#ffffff',
        'text': '#082f49',
        'accent': '#06b6d4'
    },
    'forest': {
        'primary': '#10b981',
        'secondary': '#059669',
        'background': '#ecfdf5',
        'surface': '#ffffff',
        'text': '#064e3b',
        'accent': '#065f46'
    },
    'sunset': {
        'primary': '#f59e0b',
        'secondary': '#d97706',
        'background': '#fffbeb',
        'surface': '#ffffff',
        'text': '#78350f',
        'accent': '#ea580c'
    }
}

# Layout definition
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("🌌 Enhanced Quantum Hybrid Portfolio Dashboard",
                 style={'textAlign': 'center', 'marginBottom': 30, 'color': '#1a1a1a'}),
        
        # Theme Selector
        html.Div([
            html.Label("Theme:", style=COMMON_LABEL_STYLE),
            dcc.Dropdown(
                id='theme-selector',
                options=[
                    {'label': 'Default', 'value': 'default'},
                    {'label': 'Ocean', 'value': 'ocean'},
                    {'label': 'Forest', 'value': 'forest'},
                    {'label': 'Sunset', 'value': 'sunset'}
                ],
                value='default'
            )
        ], style={'width': '15%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px'})
    ], style={'backgroundColor': '#f0f0f0', 'padding': '20px', 'borderBottom': '1px solid #ccc'}),

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
            html.Label("Evolution Time:", style=COMMON_LABEL_STYLE),
            dcc.Slider(id='evolution-time-slider', min=1, max=50, value=10, step=1),

            html.Br(),
            html.Label("Optimization Algorithm:", style=COMMON_LABEL_STYLE),
            dcc.Dropdown(
                id='algorithm-selector',
                options=[
                    {'label': 'Standard QSW', 'value': 'standard'},
                    {'label': 'Enhanced QSW', 'value': 'enhanced'},
                    {'label': 'Quantum Annealing', 'value': 'annealing'}
                ],
                value='standard'
            ),

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
                    'width': '19%', 'display': 'inline-block', 'text-align': 'center',
                    'backgroundColor': '#e5e7eb', 'padding': '20px', 'margin': '5px',
                    'borderRadius': '10px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)', 'color': '#1a1a1a'
                }),

                html.Div([
                    html.H4("Expected Return", style={'color': '#1a1a1a', 'margin': '0 0 8px 0'}),
                    html.H2(id="return-value", children="0.00%", style={'color': '#1a1a1a', 'margin': 0})
                ], className="metric-card", style={
                    'width': '19%', 'display': 'inline-block', 'text-align': 'center',
                    'backgroundColor': '#e5e7eb', 'padding': '20px', 'margin': '5px',
                    'borderRadius': '10px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)', 'color': '#1a1a1a'
                }),

                html.Div([
                    html.H4("Risk (Volatility)", style={'color': '#1a1a1a', 'margin': '0 0 8px 0'}),
                    html.H2(id="volatility-value", children="0.00%", style={'color': '#1a1a1a', 'margin': 0})
                ], className="metric-card", style={
                    'width': '19%', 'display': 'inline-block', 'text-align': 'center',
                    'backgroundColor': '#e5e7eb', 'padding': '20px', 'margin': '5px',
                    'borderRadius': '10px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)', 'color': '#1a1a1a'
                }),

                html.Div([
                    html.H4("Turnover", style={'color': '#1a1a1a', 'margin': '0 0 8px 0'}),
                    html.H2(id="turnover-value", children="0.00%", style={'color': '#1a1a1a', 'margin': 0})
                ], className="metric-card", style={
                    'width': '19%', 'display': 'inline-block', 'text-align': 'center',
                    'backgroundColor': '#e5e7eb', 'padding': '20px', 'margin': '5px',
                    'borderRadius': '10px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)', 'color': '#1a1a1a'
                }),

                html.Div([
                    html.H4("Diversification", style={'color': '#1a1a1a', 'margin': '0 0 8px 0'}),
                    html.H2(id="diversification-value", children="0.00", style={'color': '#1a1a1a', 'margin': 0})
                ], className="metric-card", style={
                    'width': '19%', 'display': 'inline-block', 'text-align': 'center',
                    'backgroundColor': '#e5e7eb', 'padding': '20px', 'margin': '5px',
                    'borderRadius': '10px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)', 'color': '#1a1a1a'
                }),
            ]),

            # Tabs for different views
            dcc.Tabs(id="tabs", value='overview', children=[
                dcc.Tab(label='Overview', value='overview'),
                dcc.Tab(label='Allocation', value='allocation'),
                dcc.Tab(label='Risk Analysis', value='risk'),
                dcc.Tab(label='Performance', value='performance'),
                dcc.Tab(label='Sensitivity', value='sensitivity')
            ]),

            # Tab content
            html.Div(id='tabs-content')

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
    Output('tabs-content', 'children'),
    [Input('tabs', 'value'),
     Input('run-btn', 'n_clicks')],
    [State('n-assets-slider', 'value'),
     State('market-regime-dropdown', 'value'),
     State('omega-slider', 'value'),
     State('evolution-time-slider', 'value'),
     State('algorithm-selector', 'value')])
def render_tabs(tab, n_clicks, n_assets, market_regime, omega, evolution_time, algorithm):
    """Render content based on selected tab."""
    # Generate data based on current settings
    if n_clicks == 0:
        # Initial load with mock data
        data = generate_mock_portfolio_data()
    else:
        # Simulate quantum optimization
        try:
            # Create mock returns and covariance
            np.random.seed(42 + n_clicks)  # For consistent results per simulation
            returns = np.random.uniform(0.05, 0.15, n_assets)
            A = np.random.randn(n_assets, n_assets)
            covariance = np.dot(A.T, A) / n_assets
            
            # Create custom config with selected parameters
            config = QSWConfig(default_omega=omega, evolution_time=evolution_time)
            
            # Select algorithm based on user choice
            if algorithm == 'enhanced':
                optimizer = EnhancedQuantumStochasticWalkOptimizer(config)
                result = optimizer.optimize(returns, covariance, market_regime=market_regime)
                
                # Format data for dashboard
                assets = [f'ASSET_{i+1}' for i in range(n_assets)]
                sectors = ['Tech', 'Finance', 'Healthcare', 'Consumer', 'Energy'] * (n_assets // 5 + 1)
                sectors = sectors[:n_assets]
                
                data = {
                    'assets': assets,
                    'sectors': sectors,
                    'returns': result.expected_return * np.ones(n_assets),  # Simulated individual returns
                    'volatility': np.sqrt(np.diag(covariance)),  # Individual volatilities
                    'weights': result.weights,
                    'sharpe_ratios': returns / np.sqrt(np.diag(covariance)),
                    'correlation_matrix': np.corrcoef(np.random.multivariate_normal(returns, covariance, size=100).T),
                    'overall_metrics': {
                        'sharpe': result.sharpe_ratio,
                        'return': result.expected_return,
                        'volatility': result.volatility,
                        'turnover': result.turnover,
                        'n_assets': len(result.weights),
                        'diversification_ratio': result.diversification_ratio,
                        'information_ratio': result.information_ratio,
                        'max_drawdown': result.max_drawdown,
                        'alpha': result.alpha,
                        'beta': result.beta
                    }
                }
            elif algorithm == 'annealing':
                optimizer = QuantumAnnealingOptimizer()
                result = optimizer.optimize(returns, covariance, market_regime=market_regime)
                
                # Format data for dashboard
                assets = [f'ASSET_{i+1}' for i in range(n_assets)]
                sectors = ['Tech', 'Finance', 'Healthcare', 'Consumer', 'Energy'] * (n_assets // 5 + 1)
                sectors = sectors[:n_assets]
                
                data = {
                    'assets': assets,
                    'sectors': sectors,
                    'returns': result['expected_return'] * np.ones(n_assets),  # Simulated individual returns
                    'volatility': np.sqrt(np.diag(covariance)),  # Individual volatilities
                    'weights': result['weights'],
                    'sharpe_ratios': returns / np.sqrt(np.diag(covariance)),
                    'correlation_matrix': np.corrcoef(np.random.multivariate_normal(returns, covariance, size=100).T),
                    'overall_metrics': {
                        'sharpe': result['sharpe_ratio'],
                        'return': result['expected_return'],
                        'volatility': result['volatility'],
                        'turnover': 0.1,  # Placeholder
                        'n_assets': result['n_active'],
                        'diversification_ratio': 0.75,  # Placeholder
                        'information_ratio': 0.85,  # Placeholder
                        'max_drawdown': 0.12,  # Placeholder
                        'alpha': 0.03,  # Placeholder
                        'beta': 0.95  # Placeholder
                    }
                }
            else:  # Standard QSW
                optimizer = QuantumStochasticWalkOptimizer(config)
                result = optimizer.optimize(returns, covariance, market_regime=market_regime)
                
                # Format data for dashboard
                assets = [f'ASSET_{i+1}' for i in range(n_assets)]
                sectors = ['Tech', 'Finance', 'Healthcare', 'Consumer', 'Energy'] * (n_assets // 5 + 1)
                sectors = sectors[:n_assets]
                
                data = {
                    'assets': assets,
                    'sectors': sectors,
                    'returns': result.expected_return * np.ones(n_assets),  # Simulated individual returns
                    'volatility': np.sqrt(np.diag(covariance)),  # Individual volatilities
                    'weights': result.weights,
                    'sharpe_ratios': returns / np.sqrt(np.diag(covariance)),
                    'correlation_matrix': np.corrcoef(np.random.multivariate_normal(returns, covariance, size=100).T),
                    'overall_metrics': {
                        'sharpe': result.sharpe_ratio,
                        'return': result.expected_return,
                        'volatility': result.volatility,
                        'turnover': result.turnover,
                        'n_assets': len(result.weights),
                        'diversification_ratio': 0.75,  # Placeholder
                        'information_ratio': 0.85,  # Placeholder
                        'max_drawdown': 0.12,  # Placeholder
                        'alpha': 0.03,  # Placeholder
                        'beta': 0.95  # Placeholder
                    }
                }
        except Exception as e:
            # Fallback to mock data if actual optimization fails
            data = generate_mock_portfolio_data()

    if tab == 'overview':
        return html.Div([
            # Charts Row 1
            html.Div([
                html.Div([
                    dcc.Graph(
                        id='allocation-chart',
                        figure=create_portfolio_allocation_donut(
                            data['weights'],
                            data['assets'],
                            title='Portfolio Allocation'
                        ).update_layout(height=400)
                    )
                ], style={'width': '50%', 'display': 'inline-block'}),

                html.Div([
                    dcc.Graph(
                        id='performance-chart',
                        figure=go.Figure(data=[
                            go.Bar(x=data['assets'], y=data['returns']*100,
                                   name='Expected Return %',
                                   marker_color='skyblue')
                        ]).update_layout(
                            title='Expected Returns by Asset',
                            xaxis_title='Assets',
                            yaxis_title='Expected Return (%)',
                            height=400,
                            paper_bgcolor='#f5f5f5', plot_bgcolor='#f5f5f5',
                            font=dict(color='#1a1a1a', size=12),
                            title_font=dict(size=14, color='#1a1a1a')
                        )
                    )
                ], style={'width': '50%', 'display': 'inline-block'}),
            ], style={'width': '100%'}),

            # Charts Row 2
            html.Div([
                html.Div([
                    dcc.Graph(
                        id='risk-return-chart',
                        figure=create_risk_return_scatter(
                            data['returns'],
                            data['volatility'],
                            data['weights'],
                            data['sharpe_ratios'],
                            data['assets'],
                            title='Risk vs Return Scatter Plot'
                        )
                    )
                ], style={'width': '50%', 'display': 'inline-block'}),

                html.Div([
                    dcc.Graph(
                        id='graph-visualization',
                        figure=create_correlation_heatmap(
                            data['correlation_matrix'],
                            data['assets'][:min(10, len(data['assets']))],  # Limit for readability
                            title='Asset Correlation Heatmap'
                        ).update_layout(height=400)
                    )
                ], style={'width': '50%', 'display': 'inline-block'}),
            ], style={'width': '100%'}),
        ])
    
    elif tab == 'allocation':
        return html.Div([
            html.Div([
                html.Div([
                    dcc.Graph(
                        id='allocation-donut',
                        figure=create_portfolio_allocation_donut(
                            data['weights'],
                            data['assets'],
                            title='Portfolio Allocation'
                        ).update_layout(height=500)
                    )
                ], style={'width': '50%', 'display': 'inline-block'}),
                
                html.Div([
                    dcc.Graph(
                        id='sector-bar',
                        figure=create_sector_allocation_bar(
                            {sector: np.sum([data['weights'][i] for i, s in enumerate(data['sectors']) if s == sector]) 
                             for sector in set(data['sectors'])},
                            title='Sector Allocation'
                        ).update_layout(height=500)
                    )
                ], style={'width': '50%', 'display': 'inline-block'}),
            ], style={'width': '100%'}),
            
            # Detailed allocation table
            html.H4("Detailed Allocation", style={'marginTop': '20px'}),
            html.Table([
                html.Thead([
                    html.Tr([html.Th(col, style={'color': '#1a1a1a', 'padding': '8px', 'textAlign': 'left', 'borderBottom': '2px solid #1a1a1a'}) 
                            for col in ['Asset', 'Sector', 'Weight %', 'Expected Return %', 'Risk %']])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td(data['assets'][i], style={'color': '#1a1a1a', 'padding': '8px', 'borderBottom': '1px solid #ccc'}),
                        html.Td(data['sectors'][i], style={'color': '#1a1a1a', 'padding': '8px', 'borderBottom': '1px solid #ccc'}),
                        html.Td(f"{data['weights'][i]*100:.2f}", style={'color': '#1a1a1a', 'padding': '8px', 'borderBottom': '1px solid #ccc', 'textAlign': 'right'}),
                        html.Td(f"{data['returns'][i]*100:.2f}", style={'color': '#1a1a1a', 'padding': '8px', 'borderBottom': '1px solid #ccc', 'textAlign': 'right'}),
                        html.Td(f"{data['volatility'][i]*100:.2f}", style={'color': '#1a1a1a', 'padding': '8px', 'borderBottom': '1px solid #ccc', 'textAlign': 'right'})
                    ]) for i in range(len(data['assets']))
                ])
            ], style={
                'width': '100%',
                'borderCollapse': 'collapse',
                'marginTop': '10px'
            })
        ])
    
    elif tab == 'risk':
        return html.Div([
            html.Div([
                html.Div([
                    dcc.Graph(
                        id='factor-risk',
                        figure=create_factor_risk_decomposition(
                            {
                                'Market': 0.35,
                                'Size': 0.15,
                                'Value': 0.20,
                                'Momentum': 0.10,
                                'Quality': 0.12,
                                'Volatility': 0.08
                            },
                            title='Factor Risk Decomposition'
                        ).update_layout(height=500)
                    )
                ], style={'width': '50%', 'display': 'inline-block'}),
                
                html.Div([
                    dcc.Graph(
                        id='turnover-analysis',
                        figure=create_portfolio_turnover_analysis(
                            [np.random.uniform(0.05, 0.15) for _ in range(20)],  # Mock turnover history
                            title='Portfolio Turnover Analysis'
                        ).update_layout(height=500)
                    )
                ], style={'width': '50%', 'display': 'inline-block'}),
            ], style={'width': '100%'}),
            
            html.Div([
                html.Div([
                    dcc.Graph(
                        id='monte-carlo',
                        figure=create_monte_carlo_simulation(
                            data['returns'],
                            title='Monte Carlo Simulation'
                        ).update_layout(height=500)
                    )
                ], style={'width': '100%', 'display': 'inline-block'}),
            ], style={'width': '100%', 'marginTop': '20px'})
        ])
    
    elif tab == 'performance':
        return html.Div([
            html.Div([
                html.Div([
                    dcc.Graph(
                        id='benchmark-comparison',
                        figure=create_performance_benchmark_comparison(
                            [
                                data['overall_metrics'],
                                {
                                    'sharpe_ratio': data['overall_metrics']['sharpe'] * 0.8,
                                    'expected_return': data['overall_metrics']['return'] * 0.9,
                                    'volatility': data['overall_metrics']['volatility'] * 1.1,
                                    'turnover': data['overall_metrics']['turnover'] * 1.5,
                                    'weights': data['weights']
                                }
                            ],
                            ['QSW Portfolio', 'Benchmark'],
                            title='Performance Comparison'
                        ).update_layout(height=500)
                    )
                ], style={'width': '100%', 'display': 'inline-block'}),
            ], style={'width': '100%'}),
            
            html.Div([
                html.Div([
                    dcc.Graph(
                        id='time-series-performance',
                        figure=create_time_series_performance(
                            [100000 * (1 + np.random.uniform(-0.02, 0.03))**i for i in range(252)],
                            [100000 * (1 + np.random.uniform(-0.015, 0.02))**i for i in range(252)],
                            title='Portfolio Performance Over Time'
                        ).update_layout(height=500)
                    )
                ], style={'width': '100%', 'display': 'inline-block'}),
            ], style={'width': '100%', 'marginTop': '20px'})
        ])
    
    elif tab == 'sensitivity':
        return html.Div([
            html.H4("Parameter Sensitivity Analysis", style={'textAlign': 'center'}),
            html.P("Analyze how changes in quantum parameters affect portfolio performance.", 
                   style={'textAlign': 'center', 'color': '#666', 'marginBottom': '20px'}),
            
            html.Div([
                html.Div([
                    html.H5("Omega (ω) Sensitivity", style={'textAlign': 'center'}),
                    dcc.Graph(
                        id='omega-sensitivity',
                        figure=go.Figure().add_trace(
                            go.Scatter(
                                x=[0.1, 0.2, 0.3, 0.4, 0.5],
                                y=[1.2, 1.4, 1.5, 1.45, 1.3],
                                mode='lines+markers',
                                name='Sharpe Ratio',
                                line=dict(color='#3B82F6', width=3),
                                marker=dict(size=8)
                            )
                        ).update_layout(
                            title='Sharpe Ratio vs Omega Parameter',
                            xaxis_title='Omega (ω)',
                            yaxis_title='Sharpe Ratio',
                            height=400
                        )
                    )
                ], style={'width': '50%', 'display': 'inline-block'}),
                
                html.Div([
                    html.H5("Evolution Time Sensitivity", style={'textAlign': 'center'}),
                    dcc.Graph(
                        id='time-sensitivity',
                        figure=go.Figure().add_trace(
                            go.Scatter(
                                x=[1, 5, 10, 15, 20, 25, 30],
                                y=[1.3, 1.45, 1.5, 1.48, 1.42, 1.35, 1.3],
                                mode='lines+markers',
                                name='Sharpe Ratio',
                                line=dict(color='#10B981', width=3),
                                marker=dict(size=8)
                            )
                        ).update_layout(
                            title='Sharpe Ratio vs Evolution Time',
                            xaxis_title='Evolution Time',
                            yaxis_title='Sharpe Ratio',
                            height=400
                        )
                    )
                ], style={'width': '50%', 'display': 'inline-block'}),
            ], style={'width': '100%'})
        ])


@app.callback(
    [Output('sharpe-value', 'children'),
     Output('return-value', 'children'),
     Output('volatility-value', 'children'),
     Output('turnover-value', 'children'),
     Output('diversification-value', 'children'),
     Output('portfolio-details', 'children'),
     Output('optimization-status', 'children')],
    [Input('run-btn', 'n_clicks')],
    [State('n-assets-slider', 'value'),
     State('market-regime-dropdown', 'value'),
     State('omega-slider', 'value'),
     State('evolution-time-slider', 'value'),
     State('algorithm-selector', 'value')])
def update_dashboard_metrics(n_clicks, n_assets, market_regime, omega, evolution_time, algorithm):
    """Update dashboard metrics with new optimization results."""
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
            
            # Create custom config with selected parameters
            config = QSWConfig(default_omega=omega, evolution_time=evolution_time)
            
            # Select algorithm based on user choice
            if algorithm == 'enhanced':
                optimizer = EnhancedQuantumStochasticWalkOptimizer(config)
                result = optimizer.optimize(returns, covariance, market_regime=market_regime)
                
                data = {
                    'overall_metrics': {
                        'sharpe': result.sharpe_ratio,
                        'return': result.expected_return,
                        'volatility': result.volatility,
                        'turnover': result.turnover,
                        'diversification_ratio': result.diversification_ratio
                    }
                }
            elif algorithm == 'annealing':
                optimizer = QuantumAnnealingOptimizer()
                result = optimizer.optimize(returns, covariance, market_regime=market_regime)
                
                data = {
                    'overall_metrics': {
                        'sharpe': result['sharpe_ratio'],
                        'return': result['expected_return'],
                        'volatility': result['volatility'],
                        'turnover': 0.1,  # Placeholder
                        'diversification_ratio': 0.75  # Placeholder
                    }
                }
            else:  # Standard QSW
                optimizer = QuantumStochasticWalkOptimizer(config)
                result = optimizer.optimize(returns, covariance, market_regime=market_regime)
                
                data = {
                    'overall_metrics': {
                        'sharpe': result.sharpe_ratio,
                        'return': result.expected_return,
                        'volatility': result.volatility,
                        'turnover': result.turnover,
                        'diversification_ratio': 0.75  # Placeholder
                    }
                }
            
            status = f"Optimization completed! Sharpe Ratio: {data['overall_metrics']['sharpe']:.3f}"
        except Exception as e:
            # Fallback to mock data if actual optimization fails
            data = generate_mock_portfolio_data()
            status = f"Error in optimization: {str(e)}. Showing mock data."

    # Create portfolio details table
    detailed_data = pd.DataFrame({
        'Asset': [f'ASSET_{i+1}' for i in range(min(10, n_assets))],
        'Weight %': (data.get('weights', np.random.dirichlet([1.0]*n_assets))[0:min(10, n_assets)] * 100).round(2),
        'Expected Return %': (data.get('returns', np.random.uniform(0.05, 0.15, n_assets))[0:min(10, n_assets)] * 100).round(2),
        'Risk %': (data.get('volatility', np.random.uniform(0.15, 0.30, n_assets))[0:min(10, n_assets)] * 100).round(2),
        'Sharpe': (data.get('returns', np.random.uniform(0.05, 0.15, n_assets))[0:min(10, n_assets)] / 
                  data.get('volatility', np.random.uniform(0.15, 0.30, n_assets))[0:min(10, n_assets)]).round(3)
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
        f"{data['overall_metrics'].get('diversification_ratio', 0.75):.3f}",
        portfolio_details_table,
        status
    ]


# Run the app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8051)