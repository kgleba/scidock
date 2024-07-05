# SciDock

![PyPI - Version](https://img.shields.io/pypi/v/scidock)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/scidock)
[![Test with PyTest](https://github.com/kgleba/scidock/actions/workflows/test.yml/badge.svg)](https://github.com/kgleba/scidock/actions/workflows/test.yml)
[![Lint with Ruff](https://github.com/kgleba/scidock/actions/workflows/lint.yml/badge.svg)](https://github.com/kgleba/scidock/actions/workflows/lint.yml)

SciDock is a CLI tool designed to provide a user-friendly interface for finding, downloading and managing scientific articles of your interest!  

## Installation

The most preferred installation method is via [pipx](https://pipx.pypa.io), which enhances all of the benefits of the CLI application while running in an isolated environment.

```shell
pipx install scidock
```

If you don't want to install pipx, you can just run:

```shell
pip install scidock
```

Note: you must have Python 3.12+ installed!

If you want to install the application manually or plan to contribute to the project, consider the "development installation" option (see next section). Otherwise, skip it without a second thought.

### Development installation

After installing [Poetry](https://python-poetry.org/docs/#installation) on your system, run these commands:

```shell
git clone https://github.com/kgleba/scidock.git
cd scidock
poetry shell
poetry install
```

## Usage

To **initialize** a repository (and set it as a default), run:

```shell
scidock init /path/to/repository
```

To perform a **search**, execute:

```shell
scidock search 'query'
```

Note that the reason we do not explicitly ask you to provide author name/title/abstract/etc. but rather provide a free-form query is that all of this work is done in the background by Natural Language Processing models.

You can also use the `--extend` option to expand the search field (e.g., to search through abstracts). By default it is disabled, and search with free-form query is limited to titles.

The dividing line in the search engine results deserves special attention. Behind it are the works that most closely match the query and, as we think, will be most useful to you.

To try and **download** the paper with a known DOI, execute:

```shell
scidock download 'DOI'
```

To set up a **proxy** (see the ["Supported Resources"](#supported-resources) section for use cases), use `scidock config`:

```shell
scidock config proxy PROXY_TYPE IP PORT
```

where `PROXY_TYPE` is either `http` or `socks5` (depending on the type of proxy you are using).

For example:

```shell
scidock config proxy socks5 127.0.0.1 1080
```

You can now force other commands (like `search` and `download`) to make the appropriate network requests through the proxy by passing the `--proxy` flag

To **open** locally stored PDFs in your standard viewer, run with free-form request:

```shell
scidock open 'query'
```

Planning to introduce **new features** soon: e.g. to `cite` any of the papers stored in the local database.

Aesthetically pleasing demos will also appear here soon :D

## Supported resources

✔️ [CrossRef](https://www.crossref.org/) (for searching through an enormous database with extensive metadata for each entry)

✔️ [arXiv](https://arxiv.org/) (for searching and downloading freely published preprints) 

✔️ [Sci-Hub](https://sci-hub.ru/) (for downloading paywalled PDFs by given DOI; might require a proxy though)

✔️ Some resources that are known to publish works with open access: [IEEE](https://ieeexplore.ieee.org), [IntechOpen](https://www.intechopen.com/) and [MDPI](https://www.mdpi.com/)

❌ [Google Scholar](https://scholar.google.com/) (yet)

❌ [CyberLeninka](https://cyberleninka.ru/) (for Russian queries)

❌ [GeneralIndex](https://archive.org/details/GeneralIndex)

❌ Anna's Archive

## Limitations

- Proxies do not support authentication
- Performance still requires attention
- Some parts of the system are still poorly configurable or not configurable at all

Don't hesitate to open [issues](https://github.com/kgleba/scidock/issues) as the project is still in beta testing!