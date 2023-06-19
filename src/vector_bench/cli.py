import math
import os
import subprocess
from typing import Dict, Optional

import numpy as np
import typer
from parse import parse
from rich import print
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

app = typer.Typer()


@app.command()
def benchmark(
    connection_string: str,
    dimensions: int,
    n_records: int,
    index_n_lists: Optional[int] = None,
    limit: int = 10,
    probes: int = 10,
):

    return benchmark_inner(
        connection_string, dimensions, n_records, index_n_lists, limit, probes
    )


def benchmark_inner(
    connection_string: str,
    dimensions: int,
    n_records: int,
    index_n_lists: Optional[int] = None,
    limit: int = 10,
    probes: int = 10,
):

    engine = create_engine(connection_string)
    Session = sessionmaker(engine)

    with Session() as sess:
        print("Initial setup", flush=True)
        sess.execute(text("set statement_timeout = '5min'"))
        sess.execute(CREATE_EXTENSION_STATEMENT)
        sess.execute(DROP_SCHEMA_STATEMENT)
        sess.execute(CREATE_SCHEMA_STATEMENT)
        sess.execute(CREATE_ARRAY_FUNCTION)
        print("Creating and populating table", flush=True)
        sess.execute(create_populated_table_statement(dimensions, n_records))
        print("Creating index", flush=True)
        sess.execute(create_index_statement(n_records, index_n_lists))
        print("Creating benchmarking function", flush=True)
        sess.execute(create_benchmarking_function(dimensions, limit, probes))
        print("Forcing index into memory", flush=True)
        sess.execute(
            text("select vector_bench.bench_func() from generate_series(1, 50)")
        )
        print("Finalizing config", flush=True)

        sess.commit()

    print("Benchmarking")

    connection_info = parse_connection_string(connection_string)
    env = os.environ.copy()
    env["PGPASSWORD"] = connection_info["password"]
    env["PGPORT"] = connection_info["port"]
    env["PGHOST"] = connection_info["host"]
    env["PGDATABASE"] = connection_info["database"]
    env["PGUSER"] = connection_info["user"]

    with open("bench.sql", "w") as f:
        query_vec = norm_vec(dimensions)
        query_vec = ", ".join([str(x) for x in query_vec])

        f.write("select vector_bench.bench_func()")

    output = subprocess.run(
        [
            "pgbench",
            "-r",
            "-h",
            connection_info["host"],
            "-U",
            connection_info["user"],
            "-T",
            "10",
            "-f",
            f.name,
            "-c",
            "150",
            "-j",
            "8",
            connection_info["database"],
        ],
        env=env,
        capture_output=True,
    )

    txt = output.stdout.decode()
    print(txt)
    return txt


@app.command()
def version():
    print("vector_bench v0.0.1")


if __name__ == "__main__":
    app()


CREATE_EXTENSION_STATEMENT = text("create extension if not exists vector;")
DROP_SCHEMA_STATEMENT = text("drop schema if exists vector_bench cascade;")
CREATE_SCHEMA_STATEMENT = text("create schema if not exists vector_bench;")

CREATE_ARRAY_FUNCTION = text(
    """
create or replace function vector_bench.generate_normalized_array(dimension int)
	returns double precision[]
    language sql
as $$
    with unnormed(elem) as(
        select random() from generate_series(1, $1) v(x)
    ),
    norm(factor) as (
        select
            sqrt(sum(pow(elem, 2)))
        from
            unnormed
    )
    select
        array_agg(u.elem / r.factor)
    from
        unnormed u, norm r

$$;
"""
)


def create_populated_table_statement(dimensions: int, n_records: int):
    return text(
        f"""
	drop table if exists vector_bench.xxx;

	create table vector_bench.xxx as
		select v.id, vector_bench.generate_normalized_array({dimensions})::vector({dimensions}) as vec
		from generate_series(1, {n_records}) v(id);
	"""
    )


def create_index_statement(n_records: int, n_lists: Optional[int] = None):
    index_n_lists = n_lists or (
        int(max(n_records / 1000, 10))
        if n_records < 1_000_000
        else int(math.sqrt(n_records))
    )

    return text(
        f"""
	create index ix_ip_100_xxx
		on vector_bench.xxx
		using ivfflat (vec vector_ip_ops) with (lists={index_n_lists})
	"""
    )


def create_benchmarking_function(dimensions: int, limit: int, probes: int):
    return text(
        f"""
    create or replace function vector_bench.bench_func(query_vec double precision[] default null, probes int default {probes})
    returns setof int
    language plpgsql
        as $$
        begin
            set enable_seqscan = off;
            execute format('set ivfflat.probes = %s', probes);
            return query
                select id
                from vector_bench.xxx
                order by vec <#> case
                    when query_vec is null then (select vector_bench.generate_normalized_array({dimensions})::vector({dimensions}))
                    else query_vec::vector({dimensions})
                end
                limit {limit};
        end;
        $$;
	"""
    )


def parse_connection_string(connection_string) -> Dict:
    connection_template = "postgresql://{user}:{password}@{host}:{port}/{database}"
    return parse(connection_template, connection_string)


def norm_vec(l):
    x = np.random.rand(l)
    return x / np.linalg.norm(x)
