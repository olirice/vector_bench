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
):

    engine = create_engine(connection_string)
    Session = sessionmaker(engine)

    with Session() as sess:

        print("Initial setup")
        sess.execute(DROP_SCHEMA_STATEMENT)
        sess.execute(CREATE_SCHEMA_STATEMENT)
        sess.execute(CREATE_ARRAY_FUNCTION)
        print("Creating and populating table")
        sess.execute(create_populated_table_statement(dimensions, n_records))
        print("Creating index")
        sess.execute(create_index_statement(n_records, index_n_lists))
        print("Creating benchmarking function")
        sess.execute(create_benchmarking_function(dimensions, limit))
        print("Finalizing config")
        sess.execute(text("set ivfflat.nprobes = 10;"))

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

    print(output.stdout.decode())


@app.command()
def version():
    print("vector_bench v0.0.1")


if __name__ == "__main__":
    app()


DROP_SCHEMA_STATEMENT = text("drop schema if exists vector_bench cascade;")
CREATE_SCHEMA_STATEMENT = text("create schema if not exists vector_bench;")

CREATE_ARRAY_FUNCTION = text(
    """
create or replace function vector_bench.generate_normalized_array(dimension int)
	returns double precision[]
as $$
	declare
	  unit_vector double precision[] := array[]::double precision[];
	  normalization_factor double precision;
	  i int;
	begin
	  if dimension <= 0 then
		raise 'Dimension should be greater than 0';
	  end if;

	  -- Create the initial array with values 1/dimension
	  for i in 1..dimension loop
		unit_vector := array_append(unit_vector, random()::double precision);
	  end loop;

	  -- Calculate normalization factor
	  normalization_factor := sqrt(dimension);

	  -- Normalize the vector
	  for i in array_lower(unit_vector, 1)..array_upper(unit_vector, 1) loop
		unit_vector[i] := unit_vector[i]/normalization_factor;
	  end loop;

	  return unit_vector;
	end;
$$ language plpgsql;
"""
)


def create_populated_table_statement(dimensions: int, n_records: int):
    return text(
        f"""
	drop table if exists vector_bench.xxx;

	create table vector_bench.xxx as
		select v.id, generate_normalized_array({dimensions})::vector({dimensions}) as vec
		from generate_series(1, {n_records}) v(id);
	"""
    )


def create_index_statement(n_records: int, n_lists: Optional[int] = None):
    index_n_lists = n_lists or (
        int(max(n_records / 1000, 30))
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


def create_benchmarking_function(dimensions: int, limit: int):
    return text(
        f"""
    create or replace function vector_bench.bench_func()
    returns setof int
        language sql
        as $$
            select id from vector_bench.xxx order by vec <#> (select generate_normalized_array({dimensions})::vector({dimensions}))  limit {limit}
        $$;
	"""
    )


def parse_connection_string(connection_string) -> Dict:
    connection_template = "postgresql://{user}:{password}@{host}:{port}/{database}"
    return parse(connection_template, connection_string)


def norm_vec(l):
    x = np.random.rand(l)
    return x / np.linalg.norm(x)
