# Disk Scheduling and Caching Simulation

## Overview
This Python simulation models a complex disk I/O system with advanced scheduling and caching mechanisms. The project demonstrates how different disk scheduling strategies and buffer caching techniques can impact system performance.

## Key Components

### 1. System Architecture
- **Processes**: Simulates read and write operations on disk sectors.
- **Buffer Cache**: Two-segment cache with configurable capacity.
- **Hard Drive**: Models track and sector access times.
- **Driver**: Implements different disk scheduling algorithms.
- **Scheduler**: Manages process execution and disk operations.

### 2. Disk Scheduling Strategies
The simulation supports three disk scheduling algorithms:
- **FIFO (First-In-First-Out)**: Basic scheduling with no track optimization.
- **LOOK**: Optimizes disk head movement by scanning in a single direction.
- **NLOOK (N-Look)**: Advanced strategy with multiple request queues.

### 3. Buffer Caching
Implements a two-segment buffer cache with:
- Configurable total and right-segment capacity.
- Intelligent buffer replacement strategy.
- Tracking of cache hits and misses.

## Performance Metrics
- Tracks total system time.
- Measures disk operation times.
- Simulates realistic disk access characteristics.

## Requirements
- **Python 3.7+**
- No external dependencies required.

## Usage

### Running the Simulation
```bash
python main.py [STRATEGY]
```


### License
Open-source project for educational and research purposes.

### Contributing
Contributions, issues, and feature requests are welcome!
