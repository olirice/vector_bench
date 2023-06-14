# Vector Bench

A minimal utility for benchmarking pgvector


## Installing

Requirements:
- python 3.8+
- pgbench

```
pip install git+https://github.com/olirice/vector_bench.git
```

## Benchmark CLI

```
$ vector_bench benchmark --help

 Usage: vector_bench benchmark [OPTIONS] CONNECTION_STRING DIMENSIONS N_RECORDS

╭─ Arguments ───────────────────────────────────────────────────────────────────────╮
│ *    connection_string      TEXT     [default: None] [required]                   │
│ *    dimensions             INTEGER  [default: None] [required]                   │
│ *    n_records              INTEGER  [default: None] [required]                   │
╰───────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ─────────────────────────────────────────────────────────────────────────╮
│ --index-n-lists        INTEGER  [default: None]                                   │
│ --limit                INTEGER  [default: 10]                                     │
│ --probes               INTEGER  [default: 10]                                     │
│ --help                          Show this message and exit.                       │
╰───────────────────────────────────────────────────────────────────────────────────╯
```

## Example Usage

Command

```
vector_bench benchmark 'postgresql://postgres:<password>@db.<project_ref>.supabase.co:6543/postgres' 960 100000
```

Output

```
Initial setup
Creating and populating table
Creating index
Finalizing config
Benchmarking
pgbench (15.3, server 15.1)
transaction type: bench.sql
scaling factor: 1
query mode: simple
number of clients: 150
number of threads: 8
maximum number of tries: 1
duration: 10 s
number of transactions actually processed: 10112
number of failed transactions: 0 (0.000%)
latency average = 114.126 ms
initial connection time = 2419.960 ms
tps = 1314.338679 (without initial connection time)   <------- Transactions per second
statement latencies in milliseconds and failures:
       113.551           0  select id from vector_bench.xxx order by vec <#> '[0.05532938334987327,
0.0036667510917421427, 0.042280200655183495, 0.02285502
```


## Help

```
$ vector_bench --help

 Usage: vector_bench [OPTIONS] COMMAND [ARGS]...

╭─ Options ────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.  │
│ --show-completion             Show completion for the current shell,  ...│
│ --help                        Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────╮
│ benchmark                                                                │
╰──────────────────────────────────────────────────────────────────────────╯
```




