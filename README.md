# SciDock Alpha

## Installation

Soon this project will be published on [PyPI](https://pypi.org/), and `pip` will become the preferred installation method.

### Development installation

After installing [Poetry](https://python-poetry.org/docs/#installation) on your system, run these commands:

```shell
git clone https://github.com/kgleba/scidock.git
cd scidock
poetry shell
poetry install
```

## Usage

Note: in the future, SciDock will become a full-fledged console application and will be called with the `scidock` command. To emulate this behavior at this stage of development, we use `poetry run`.

To initialize a repository (and set it as a default), run:

```shell
poetry run scidock init /path/to/repository
```

To perform a search, execute:

```shell
poetry run scidock search 'query'
```

Note that the reason we do not explicitly ask you to provide author name/title/abstract/etc. but rather provide a free-form query is that all of this work is done in the background by Natural Language Processing models.

To try and download the paper with a known DOI, execute:

```shell
poetry run scidock download 'DOI'
```

To set up a proxy (see the ["Supported Resources"](#supported-resources) section for use cases), use `scidock config`:

```shell
poetry run scidock config proxy PROXY_TYPE IP PORT
```

where `PROXY_TYPE` is either `http` or `socks5` (depending on the type of proxy you are using).

For example:

```shell
poetry run scidock config proxy socks5 127.0.0.1 1080
```

You can now force other commands (like `search` and `download`) to make the appropriate network requests through the proxy by passing the `--proxy` flag

Planning to introduce **new features** soon: the ability to `open` locally stored PDFs in your standard viewer on free-form request; and to `cite` any of the papers stored in the local database.

Aesthetically pleasing demos will also appear here soon :D

## Supported resources

✔️ [CrossRef](https://www.crossref.org/) (for searching through an enormous database with extensive metadata for each entry)

✔️ [arXiv](https://arxiv.org/) (for searching and downloading freely published preprints) 

✔️ [Sci-Hub](https://sci-hub.ru/) (for downloading paywalled PDFs by given DOI; might require a proxy though)

❌ [Google Scholar](https://scholar.google.com/) (yet)

❌ [GeneralIndex](https://archive.org/details/GeneralIndex)

❌ Anna's Archive

## Limitations

- Proxies do not support authentication
- Performance still isn't fascinating
- Some parts of the system are still poorly configurable or not configurable at all