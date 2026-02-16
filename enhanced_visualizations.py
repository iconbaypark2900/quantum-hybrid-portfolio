"""
Enhanced visualization components for the Quantum Hybrid Portfolio Dashboard.
This module contains advanced visualization components that improve upon the basic dashboard.
"""
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import pandas as pd
import networkx as nx
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import plotly.subplots as sp

def create_correlation_heatmap(corr_matrix: np.ndarray, 
                             asset_names: List[str],
                             title: str = "Asset Correlation Heatmap") -> go.Figure:
    """
    Create an enhanced correlation heatmap with improved interactivity and styling.
    
    Args:
        corr_matrix: Correlation matrix
        asset_names: Names of assets
        title: Title for the heatmap
    
    Returns:
        Plotly Figure object
    """
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix,
        x=asset_names,
        y=asset_names,
        colorscale='RdBu',
        zmid=0,
        hoverongaps=False,
        hovertemplate='<b>%{x}</b> vs <b>%{y}</b><br>' +
                     'Correlation: %{z:.3f}<extra></extra>',
        colorbar=dict(
            title="Correlation",
            tickmode="array",
            tickvals=[-1, -0.5, 0, 0.5, 1],
            ticktext=["-1", "-0.5", "0", "0.5", "1"]
        )
    ))
    
    fig.update_layout(
        title=title,
        xaxis=dict(tickangle=-45, side='top'),
        yaxis=dict(autorange='reversed'),
        width=800,
        height=800,
        template='plotly_white'
    )
    
    return fig


def create_risk_return_scatter(returns: np.ndarray,
                              volatility: np.ndarray,
                              weights: np.ndarray,
                              sharpe_ratios: np.ndarray,
                              asset_names: List[str],
                              title: str = "Risk-Return Scatter Plot") -> go.Figure:
    """
    Create an enhanced risk-return scatter plot with bubble sizing and color mapping.
    
    Args:
        returns: Expected returns for each asset
        volatility: Volatility for each asset
        weights: Portfolio weights
        sharpe_ratios: Sharpe ratios for each asset
        asset_names: Names of assets
        title: Title for the plot
    
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    # Add portfolio assets (in portfolio)
    in_portfolio_mask = weights > 0.005  # Assets with meaningful weights
    if np.any(in_portfolio_mask):
        fig.add_trace(go.Scatter(
            x=volatility[in_portfolio_mask] * 100,
            y=returns[in_portfolio_mask] * 100,
            mode='markers+text',
            marker=dict(
                size=np.sqrt(weights[in_portfolio_mask]) * 1000,  # Square root for better visual scaling
                sizemode='diameter',
                color=sharpe_ratios[in_portfolio_mask],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Sharpe Ratio", x=1.05),
                line=dict(width=2, color='white')
            ),
            text=asset_names if len(asset_names) == len(weights) else [f"Asset {i}" for i in range(len(weights))],
            textposition="middle center",
            name="In Portfolio",
            hovertemplate='<b>%{text}</b><br>' +
                         'Risk: %{x:.2f}%<br>' +
                         'Return: %{y:.2f}%<br>' +
                         'Weight: %{marker.size:.1f}%<br>' +
                         'Sharpe: %{marker.color:.3f}<extra></extra>'
        ))
    
    # Add non-portfolio assets (not in portfolio)
    not_in_portfolio_mask = ~in_portfolio_mask
    if np.any(not_in_portfolio_mask):
        fig.add_trace(go.Scatter(
            x=volatility[not_in_portfolio_mask] * 100,
            y=returns[not_in_portfolio_mask] * 100,
            mode='markers',
            marker=dict(
                size=8,
                color='lightgray',
                opacity=0.5
            ),
            name="Not in Portfolio",
            hovertemplate='<b>%{text}</b><br>' +
                         'Risk: %{x:.2f}%<br>' +
                         'Return: %{y:.2f}%<extra></extra>',
            text=[asset_names[i] if i < len(asset_names) else f"Asset {i}" 
                  for i, mask in enumerate(not_in_portfolio_mask) if mask]
        ))
    
    # Add efficient frontier approximation
    # Sort by return and fit a curve
    sorted_indices = np.argsort(returns)
    sorted_returns = returns[sorted_indices]
    sorted_vol = volatility[sorted_indices]
    
    # Simple quadratic fit for demonstration
    coeffs = np.polyfit(sorted_vol, sorted_returns, deg=2)
    vol_range = np.linspace(sorted_vol.min(), sorted_vol.max(), 100)
    frontier_returns = np.polyval(coeffs, vol_range)
    
    fig.add_trace(go.Scatter(
        x=vol_range * 100,
        y=frontier_returns * 100,
        mode='lines',
        line=dict(color='red', dash='dash', width=2),
        name='Efficient Frontier (approx.)',
        hoverinfo='skip'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Risk (Volatility %)',
        yaxis_title='Expected Return %',
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        template='plotly_white',
        width=900,
        height=600
    )
    
    return fig


def create_portfolio_allocation_donut(weights: np.ndarray,
                                    asset_names: List[str],
                                    top_n: int = 10,
                                    title: str = "Portfolio Allocation") -> go.Figure:
    """
    Create a donut chart showing portfolio allocation with 'Others' category.
    
    Args:
        weights: Portfolio weights
        asset_names: Names of assets
        top_n: Number of top assets to show individually
        title: Title for the chart
    
    Returns:
        Plotly Figure object
    """
    # Get top N assets and group others
    sorted_indices = np.argsort(weights)[::-1]
    top_indices = sorted_indices[:top_n]
    other_indices = sorted_indices[top_n:]
    
    top_weights = weights[top_indices]
    top_names = [asset_names[i] if i < len(asset_names) else f"Asset {i}" for i in top_indices]
    
    other_weight = np.sum(weights[other_indices])
    if other_weight > 0:
        top_weights = np.append(top_weights, other_weight)
        top_names.append("Others")
    
    # Create the donut chart
    fig = go.Figure(data=[go.Pie(
        labels=top_names,
        values=top_weights * 100,  # Convert to percentage
        hole=0.4,  # Creates the donut effect
        pull=[0.05 if w > 0.05 else 0 for w in top_weights],  # Highlight large holdings
        hovertemplate='<b>%{label}</b><br>' +
                     'Weight: %{value:.2f}%<br>' +
                     '<extra></extra>',
        texttemplate='%{label}<br>%{percent}',
        textposition='inside',
        textinfo='percent'
    )])
    
    fig.update_layout(
        title=title,
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02),
        template='plotly_white',
        width=700,
        height=600
    )
    
    return fig


def create_sector_allocation_bar(sector_weights: Dict[str, float],
                               title: str = "Sector Allocation") -> go.Figure:
    """
    Create a bar chart showing allocation by sector.
    
    Args:
        sector_weights: Dictionary mapping sectors to weights
        title: Title for the chart
    
    Returns:
        Plotly Figure object
    """
    sectors = list(sector_weights.keys())
    weights = [w * 100 for w in sector_weights.values()]  # Convert to percentage
    
    colors = px.colors.qualitative.Set3[:len(sectors)]
    
    fig = go.Figure(data=[
        go.Bar(
            x=sectors,
            y=weights,
            marker_color=colors,
            text=[f'{w:.1f}%' for w in weights],
            textposition='auto',
            hovertemplate='<b>%{x}</b><br>' +
                         'Allocation: %{y:.2f}%<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title=title,
        xaxis_title='Sector',
        yaxis_title='Allocation (%)',
        template='plotly_white',
        width=800,
        height=500
    )
    
    return fig


def create_performance_benchmark_comparison(results: List[Dict],
                                         labels: List[str],
                                         title: str = "Performance Comparison") -> go.Figure:
    """
    Create a radar chart comparing multiple portfolio strategies.
    
    Args:
        results: List of dictionaries containing performance metrics for each strategy
        labels: Labels for each strategy
        title: Title for the chart
    
    Returns:
        Plotly Figure object
    """
    # Define the metrics to compare
    metrics = ['Sharpe Ratio', 'Return (%)', 'Volatility (%)', 'Turnover (%)', 'Diversification']
    
    # Normalize values for radar chart (between 0 and 1)
    normalized_data = []
    for result in results:
        row = []
        # Sharpe ratio (higher is better, normalize to 0-1 range)
        row.append(min(max(result.get('sharpe_ratio', 0) / 2.0, 0), 1))  # Assuming max sharpe of 2
        
        # Return (normalize to 0-1 range)
        row.append(min(max(result.get('expected_return', 0) * 100 / 20.0, 0), 1))  # Assuming max return of 20%
        
        # Volatility (lower is better, invert for radar chart)
        row.append(1 - min(max(result.get('volatility', 0) * 100 / 30.0, 0), 1))  # Assuming max vol of 30%
        
        # Turnover (lower is better, invert for radar chart)
        row.append(1 - min(max(result.get('turnover', 0) * 100 / 50.0, 0), 1))  # Assuming max turnover of 50%
        
        # Diversification (calculated as 1/HHI, higher is better)
        weights = result.get('weights', [])
        if len(weights) > 0:
            hhi = np.sum(np.square(weights))
            div_score = 1.0 / hhi if hhi > 0 else len(weights)  # Perfect diversification score
            # Normalize diversification score (assuming max possible is num_assets)
            norm_div = min(div_score / len(weights), 1.0) if len(weights) > 0 else 0.5
        else:
            norm_div = 0.5
        row.append(norm_div)
        
        normalized_data.append(row)
    
    # Create subplots for multiple strategies
    fig = go.Figure()
    
    for i, (data, label) in enumerate(zip(normalized_data, labels)):
        fig.add_trace(go.Scatterpolar(
            r=data + [data[0]],  # Close the shape
            theta=metrics + [metrics[0]],  # Close the shape
            fill='toself',
            name=label,
            hovertemplate='<b>%{theta}</b><br>' +
                         'Score: %{r:.3f}<extra></extra>'
        ))
    
    fig.update_layout(
        title=title,
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            ),
            angularaxis=dict(
                direction="clockwise"
            )
        ),
        showlegend=True,
        template='plotly_white',
        width=800,
        height=700
    )
    
    return fig


def create_time_series_performance(portfolio_values: List[float],
                                 benchmark_values: Optional[List[float]] = None,
                                 dates: Optional[List[datetime]] = None,
                                 title: str = "Portfolio Performance Over Time") -> go.Figure:
    """
    Create a time series chart showing portfolio performance over time.
    
    Args:
        portfolio_values: Portfolio values over time
        benchmark_values: Benchmark values for comparison (optional)
        dates: Dates corresponding to the values (optional)
        title: Title for the chart
    
    Returns:
        Plotly Figure object
    """
    if dates is None:
        dates = [datetime.today() - timedelta(days=len(portfolio_values)-i) for i in range(len(portfolio_values))]
    
    fig = go.Figure()
    
    # Portfolio performance
    fig.add_trace(go.Scatter(
        x=dates,
        y=portfolio_values,
        mode='lines',
        name='Portfolio',
        line=dict(color='#3B82F6', width=3),
        hovertemplate='<b>Portfolio</b><br>' +
                     'Date: %{x}<br>' +
                     'Value: $%{y:.2f}<extra></extra>'
    ))
    
    # Benchmark performance if provided
    if benchmark_values is not None and len(benchmark_values) == len(portfolio_values):
        fig.add_trace(go.Scatter(
            x=dates,
            y=benchmark_values,
            mode='lines',
            name='Benchmark',
            line=dict(color='#EF4444', width=2, dash='dash'),
            hovertemplate='<b>Benchmark</b><br>' +
                         'Date: %{x}<br>' +
                         'Value: $%{y:.2f}<extra></extra>'
        ))
    
    # Add range selector buttons
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title='Portfolio Value ($)',
        template='plotly_white',
        width=1000,
        height=600,
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all", label="All")
                ])
            ),
            rangeslider=dict(visible=True),
            type="date"
        )
    )
    
    return fig


def create_factor_risk_decomposition(factor_exposures: Dict[str, float],
                                   title: str = "Factor Risk Decomposition") -> go.Figure:
    """
    Create a waterfall chart showing factor risk decomposition.
    
    Args:
        factor_exposures: Dictionary mapping factors to risk contributions
        title: Title for the chart
    
    Returns:
        Plotly Figure object
    """
    factors = list(factor_exposures.keys())
    values = list(factor_exposures.values())
    
    # Create base for waterfall
    base_values = [0]
    for v in values[:-1]:
        base_values.append(base_values[-1] + v)
    
    # Create the waterfall chart
    fig = go.Figure(go.Waterfall(
        name="Risk Decomposition",
        orientation="v",
        measure=["relative"] * len(values),
        x=factors,
        text=[f"{v:.2f}%" for v in values],
        textposition="outside",
        y=values,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#10B981"}},
        decreasing={"marker": {"color": "#EF4444"}},
        totals={"marker": {"color": "#3B82F6"}}
    ))
    
    fig.update_layout(
        title=title,
        showlegend=False,
        template='plotly_white',
        width=900,
        height=500,
        yaxis_title="Risk Contribution (%)"
    )
    
    return fig


def create_portfolio_turnover_analysis(turnover_history: List[float],
                                     dates: Optional[List[datetime]] = None,
                                     title: str = "Portfolio Turnover Analysis") -> go.Figure:
    """
    Create a chart showing portfolio turnover over time.
    
    Args:
        turnover_history: Historical turnover values
        dates: Dates corresponding to the turnover values (optional)
        title: Title for the chart
    
    Returns:
        Plotly Figure object
    """
    if dates is None:
        dates = [datetime.today() - timedelta(days=len(turnover_history)-i) for i in range(len(turnover_history))]
    
    fig = go.Figure()
    
    # Turnover line
    fig.add_trace(go.Scatter(
        x=dates,
        y=[t * 100 for t in turnover_history],  # Convert to percentage
        mode='lines+markers',
        name='Turnover',
        line=dict(color='#8B5CF6', width=2),
        marker=dict(size=6),
        hovertemplate='<b>Turnover</b><br>' +
                     'Date: %{x}<br>' +
                     'Turnover: %{y:.2f}%<extra></extra>'
    ))
    
    # Add average line
    avg_turnover = np.mean([t * 100 for t in turnover_history])
    fig.add_hline(
        y=avg_turnover,
        line_dash="dash",
        line_color="#8B5CF6",
        annotation_text=f"Avg: {avg_turnover:.2f}%",
        annotation_position="top right"
    )
    
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title='Turnover (%)',
        template='plotly_white',
        width=900,
        height=500
    )
    
    return fig


def create_monte_carlo_simulation(returns: np.ndarray,
                                initial_capital: float = 100000,
                                n_simulations: int = 1000,
                                time_horizon: int = 252,  # 1 year of trading days
                                title: str = "Monte Carlo Simulation") -> go.Figure:
    """
    Create a Monte Carlo simulation of portfolio performance.
    
    Args:
        returns: Historical or expected returns
        initial_capital: Initial investment amount
        n_simulations: Number of simulation paths
        time_horizon: Number of periods to simulate
        title: Title for the chart
    
    Returns:
        Plotly Figure object
    """
    # Calculate mean and std of returns
    mean_return = np.mean(returns)
    std_return = np.std(returns)
    
    # Generate simulation paths
    np.random.seed(42)  # For reproducible results
    paths = np.zeros((time_horizon, n_simulations))
    paths[0, :] = initial_capital
    
    for t in range(1, time_horizon):
        # Random returns based on historical statistics
        random_returns = np.random.normal(mean_return, std_return, n_simulations)
        paths[t, :] = paths[t-1, :] * (1 + random_returns)
    
    # Calculate percentiles
    p5 = np.percentile(paths, 5, axis=1)
    p25 = np.percentile(paths, 25, axis=1)
    p50 = np.percentile(paths, 50, axis=1)
    p75 = np.percentile(paths, 75, axis=1)
    p95 = np.percentile(paths, 95, axis=1)
    
    # Create dates for x-axis
    dates = [datetime.today() + timedelta(days=i) for i in range(time_horizon)]
    
    fig = go.Figure()
    
    # Add confidence intervals
    fig.add_trace(go.Scatter(
        x=dates, y=p95,
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip',
        name='95%'
    ))
    
    fig.add_trace(go.Scatter(
        x=dates, y=p5,
        line=dict(width=0),
        fillcolor='rgba(239,68,68,0.2)',
        fill='tonexty',
        showlegend=False,
        hoverinfo='skip',
        name='5%'
    ))
    
    fig.add_trace(go.Scatter(
        x=dates, y=p75,
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip',
        name='75%'
    ))
    
    fig.add_trace(go.Scatter(
        x=dates, y=p25,
        line=dict(width=0),
        fillcolor='rgba(239,68,68,0.4)',
        fill='tonexty',
        showlegend=False,
        hoverinfo='skip',
        name='25%'
    ))
    
    # Add median path
    fig.add_trace(go.Scatter(
        x=dates, y=p50,
        line=dict(color='blue', width=2),
        name='Median Path',
        hovertemplate='<b>Median</b><br>' +
                     'Date: %{x}<br>' +
                     'Value: $%{y:,.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title='Portfolio Value ($)',
        template='plotly_white',
        width=1000,
        height=600
    )
    
    return fig