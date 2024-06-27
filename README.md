# SciDock

SciDock is a CLI tool designed to provide a user-friendly interface for finding, downloading and managing scientific articles of your interest!  

## Installation

```shell
pip install scidock
```

You must have Python 3.12+ installed!

### Development installation

After installing [Poetry](https://python-poetry.org/docs/#installation) on your system, run these commands:

```shell
git clone https://github.com/kgleba/scidock.git
cd scidock
poetry shell
poetry install
```

## Usage

To initialize a repository (and set it as a default), run:

```shell
scidock init /path/to/repository
```

To perform a search, execute:

```shell
scidock search 'query'
```

Note that the reason we do not explicitly ask you to provide author name/title/abstract/etc. but rather provide a free-form query is that all of this work is done in the background by Natural Language Processing models.

To try and download the paper with a known DOI, execute:

```shell
scidock download 'DOI'
```

To set up a proxy (see the ["Supported Resources"](#supported-resources) section for use cases), use `scidock config`:

```shell
scidock config proxy PROXY_TYPE IP PORT
```

where `PROXY_TYPE` is either `http` or `socks5` (depending on the type of proxy you are using).

For example:

```shell
scidock config proxy socks5 127.0.0.1 1080
```

You can now force other commands (like `search` and `download`) to make the appropriate network requests through the proxy by passing the `--proxy` flag

To `open` locally stored PDFs in your standard viewer, run with free-form request:

```shell
scidock open 'query'
```

Planning to introduce **new features** soon: e.g. to `cite` any of the papers stored in the local database.

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
- Performance still requires attention
- Some parts of the system are still poorly configurable or not configurable at all