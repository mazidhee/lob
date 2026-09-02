# LOB Matching Engine

High-performance limit order book with price-time priority matching.

## Quick Start

```bash
git clone https://github.com/your-org/lob-engine.git && cd lob-engine
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

## Project Structure

```text
lob-engine/
├── benchmarks/         # Performance benchmarking harness
├── docs/               # Architecture and design trade-off analysis
├── src/lob/            # Core matching engine, book side, price level DLL
└── tests/              # Unit, invariant (Hypothesis), and stress suites
```

## Key Design Decisions

- **SortedDict + Doubly Linked List (DLL)**: $O(\log P)$ price level insertion via balanced tree, $O(1)$ FIFO queue execution per level.
- **$O(1)$ Cancellations**: Hash map indexing `order_id -> (Node, Price)` enables direct pointer splice without queue traversal.
- **Strict Price-Time Priority**: Deterministic FIFO execution with in-place queue updates for non-priority-losing modifications.

## Supported Order Types

- `LIMIT`: Matches aggressively if crossable; rests remainder in book.
- `MARKET`: Matches immediately at best available prices; leaves no resting volume.
- `IOC` (Immediate-Or-Cancel): Matches available depth immediately; cancels unfilled balance.
- `FOK` (Fill-Or-Kill): Requires full fill upon arrival; cancels entirely if depth is insufficient.

## Testing

Runs unit tests, stateful property tests via Hypothesis (invariant validation), and differential testing against a naive oracle:

```bash
pytest                  # Run all tests
pytest -m "not slow"    # Fast test suite
pytest tests/property/  # Property-based invariant tests
```

## Benchmarks

Run the benchmark suite:

```bash
python benchmarks/throughput_bench.py 20000
```

Sample output:

```text
---------------------------------------------------------------------------------
Operation             Ops     Throughput      Mean       p50       p99     p99.9
---------------------------------------------------------------------------------
Insert Limit       20,000       52,410/s    19.1us    17.2us    45.8us   112.4us
Cancel             20,000      115,280/s     8.7us     7.8us    21.3us    58.1us
Mixed              20,000       48,150/s    20.8us    18.5us    52.6us   134.2us
---------------------------------------------------------------------------------
```

## License

MIT
