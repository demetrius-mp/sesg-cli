# sesg-cli

> CLI to interact with [SeSG](https://github.com/demetrius-mp/sesg).

This CLI is used by the authors to perform experimentations with the tool.

## External dependencies

- [poetry](https://python-poetry.org/). Dependency manager.
- [PostgreSQL](https://www.postgresql.org/). You can just use a PostgreSQL docker image if you wish.

## How to use

Install poetry, and create a database on postgresql. Then, create a `.env` file, using the `.env.example` file as guide. You will need to set the `SESG_DATABASE_URL` environment variable. To create the connection URL, refer to [this link](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls). The URL available at the `.env.example` expects a database named `sesg` in `localhost:5432`, with the username `postgres`, and password `postgres`.

Install the dependencies using the following command:

```sh
poetry install
```

Then to enable the `sesg` command, access the virtual environment shell with the following command:

```sh
poetry shell
```

To create the tables on the database, run the following command:

```sh
sesg db create-tables
```

To create the configuration file (`config.toml`), run the following command:

```sh
sesg config init  # [path/to/the/config.toml]
```

To get help on a command just run `sesg {command} --help`. For example. the command below will show help for the `scopus` command:

```sh
sesg scopus --help
```