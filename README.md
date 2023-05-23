# sesg-cli

> CLI to interact with [SeSG](https://github.com/demetrius-mp/sesg).

This CLI is used by the authors to perform experimentations with the tool.

## External dependencies

- [poetry](https://python-poetry.org/). Dependency manager.
- [PostgreSQL](https://www.postgresql.org/). You can just use a PostgreSQL docker image if you wish.

## How to use

Install the dependencies using the following command:

```sh
poetry install
```

Then to enable the `sesg` command, access the virtual environment shell with the following command:

```sh
poetry shell
```

To get help on a command just run `sesg {command} --help`. For example. the command below will show help for the `scopus` command:

```sh
sesg scopus --help
```