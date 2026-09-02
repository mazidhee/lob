import matplotlib.pyplot as plt
import numpy as np

plt.style.use('dark_background')
plt.rcParams.update({
    'axes.facecolor': '#1E1E1E',
    'figure.facecolor': '#121212',
    'grid.color': '#333333',
    'text.color': '#E0E0E0',
    'axes.labelcolor': '#E0E0E0',
    'xtick.color': '#E0E0E0',
    'ytick.color': '#E0E0E0',
})


def depth_chart(bids: list[tuple[float, int, int]],
                asks: list[tuple[float, int, int]]) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 6))

    if bids:
        prices, qtys = zip(*[(p, q) for p, q, _ in sorted(bids, reverse=True)])
        cum = np.cumsum(qtys)
        ax.fill_between(prices, cum, color='#00C853', alpha=0.3, step='post')
        ax.step(prices, cum, color='#00C853', where='post', label='Bids')

    if asks:
        prices, qtys = zip(*[(p, q) for p, q, _ in sorted(asks)])
        cum = np.cumsum(qtys)
        ax.fill_between(prices, cum, color='#D50000', alpha=0.3, step='pre')
        ax.step(prices, cum, color='#D50000', where='pre', label='Asks')

    ax.set_title('Market Depth')
    ax.set_xlabel('Price')
    ax.set_ylabel('Cumulative Quantity')
    ax.legend()
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    return fig


def spread_chart(timestamps, spreads) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(timestamps, spreads, color='#00B0FF')
    ax.set_title('Bid-Ask Spread')
    ax.set_xlabel('Time')
    ax.set_ylabel('Spread')
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    return fig


def imbalance_chart(timestamps, imbalances) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(timestamps, imbalances, color='#FFAB00')
    ax.axhline(0, color='#E0E0E0', linestyle='--', alpha=0.5)
    ax.set_title('Order Book Imbalance')
    ax.set_xlabel('Time')
    ax.set_ylabel('Imbalance')
    ax.set_ylim(-1.1, 1.1)
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    return fig


def trade_chart(timestamps, prices, vwap_line=None) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(timestamps, prices, color='#E040FB', s=10, alpha=0.6, label='Trades')
    if vwap_line is not None:
        ax.plot(timestamps, vwap_line, color='#FFFF00', linewidth=2, label='VWAP')
    ax.set_title('Trade Prices')
    ax.set_xlabel('Time')
    ax.set_ylabel('Price')
    ax.legend()
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    return fig


def latency_histogram(latencies_us) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(latencies_us, bins=50, color='#6200EA', alpha=0.8, edgecolor='black')
    ax.set_title('Latency Distribution')
    ax.set_xlabel('Latency (us)')
    ax.set_ylabel('Frequency')
    ax.set_yscale('log')
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    return fig
