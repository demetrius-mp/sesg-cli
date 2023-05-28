# sesg-cli

> CLI to interact with [SeSG](https://github.com/demetrius-mp/sesg).

This CLI is used by the authors to perform experimentations with the tool.

## External dependencies

- [PostgreSQL](https://www.postgresql.org/). You can just use a PostgreSQL docker image if you wish.

## How to use

Install poetry, and create a database on postgresql. Then, create a `.env` file, using the `.env.example` file as guide. You will need to set the `SESG_DATABASE_URL` environment variable. To create the connection URL, refer to [this link](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls). The URL available at the `.env.example` expects a database named `sesg` in `localhost:5432`, with the username `postgres`, and password `postgres`.

Create a virtual environment:

```sh
python -m venv .venv
```

Activate the virtual environment:

```sh
source .venv/bin/activate
```

Install the project using the following command:

```sh
pip install -e .
```

At this point, the `sesg` command is available in your shell.

To get help on a command just run `sesg {command} --help`. For example. the command below will show help for the `scopus` command:

```sh
sesg scopus --help
```

## Recommended order of commands execution

### Create the database

To create the tables on the database, run the following command:

```sh
sesg db create-tables
```

Notice that you need to create the database before running this command, since it is not capable of creating the database, only the tables.

### Saving the SLR

Create a `slr.json` file with the needed data. This file must have the following schema:

```jsonc
{
  // name of the SLR
  "name": "name",
  // GS studies of the SLR
  "gs": [
    {
      "id": 1,
      "title": "Title",
      "abstract": "Abstract",
      "keywords": "keyword 1, keyword 2, keyword 3"
    },
    {
      "id": 2,
      "title": "Title",
      "abstract": "Abstract",
      "keywords": "keyword 1, keyword 2, keyword 3"
    },
    {
      "id": 3,
      "title": "Title",
      "abstract": "Abstract",
      "keywords": "keyword 1, keyword 2, keyword 3"
    },
  ],
  // the following properties are optional
  // you can set them to use boundaries when generating
  // the search strings.
  "min_publication_year": 2000,
  "max_publication_year": 2018
}
```

Then, create a `txts/` folder. This folder must have enumerated `.cermtxt` files, starting from 1, up to the number of studies included on the SLR.

> **Warning**
> Notice that the file `1.cermtxt` must correspond to the study with id `1` on the `slr.json` file. In general, the file `i.cermtxt` must correspond to the study with id `i` on the `slr.json`.

After creating these files, save the SLR to the database with the following command. This command will also perform backward snowballing and save the citation graph.

```sh
sesg slr create-from-json path/to/slr.json path/to/txts/
```

### Create a configuration file (`config.toml`)

The configuration file will hold the parameters variations, along with your Scopus API keys. To create it, use the following command:

```sh
sesg config init  # [path/to/config.toml]
```

> **Note**
> If you do not provide a path, it will create the file on the current working directory.

### Perform an experiment

The following command will create a new experiment, with a randomized QGS:

```sh
sesg experiment start {SLR name} {experiment name}
```

Notice that the experiment will use all of the strategies available. To get help, use the following command:

```sh
sesg experiment start --help
```

You can safely stop a experiment and get back to it later if you wish. If you pass a experiment name that already exists on the database, it will retrieve this experiment and continue right from where it stopped (meaning it will generate more strings with the remaining parameters).

### Using the search strings on Scopus

To use to search strings on scopus use the following command:

```sh
sesg scopus search  # arguments and options
```

To get help, use the following command:

```sh
sesg scopus search --help
```