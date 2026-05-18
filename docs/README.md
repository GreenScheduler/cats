# CATS Documentation

This `docs/` directory provides the canonical source for the CATS
documentation, both the source content and infrastructure and the
built HTML.

## Maintenance


### About

This documentaton is made with the [Sphinx](https://www.sphinx-doc.org/)
documentation tool. This `docs/` directory contains:

* a `source/` directory containing the source content for the documentation,
  which consists of:
  * text content in
    ['RST' format](https://en.wikipedia.org/wiki/ReStructuredText) in `.rst`
    files;
  * a `conf.py` configuration file to
    [configure Sphinx](https://www.sphinx-doc.org/en/master/usage/configuration.html)
    to set up features, style as desired, and so on;
  * a `_static` directory holding 'static' content such as images and CSS
    files;
* a `build/` directory containing the built HTML content pages that form
  the online documentation;
* some `make` related files (`Makefile` and `make.bat`) to set up the
  build `make` commands.


### Building

Follow the steps below to build the documentation. Example output reports
from the Sphinx documentation builder are shown also, for illustration.

Note you will need an environment with certain libraries
installed (see 'Requirements' below), including the latest CATS because
the API reference is created using the library itself, so a copy of a
minimal working environment that enables the build to work has been
provided below.

The main command involved
is an `make html` made here in the `docs/` directory (`make clean` removes
all existing built documentation first, and it is wise practice to run it
initially):

```console
$ pwd
<path to root repository>/cats
$ cd docs
$ make clean
Removing everything under 'build'...
$ make html
Running Sphinx v4.5.0
making output directory... done
[autosummary] generating autosummary for: api-reference.rst, cli-reference.rst, contributing.rst, index.rst, installation.rst, introduction.rst, quickstart.rst, use-with-schedulers.rst
building [mo]: targets for 0 po files that are out of date
building [html]: targets for 8 source files that are out of date
updating environment: [new config] 8 added, 0 changed, 0 removed
reading sources... [100%] use-with-schedulers
pickling environment... done
checking consistency... done
preparing documents... done
writing output... [100%] use-with-schedulers
generating indices... genindex py-modindex done
writing additional pages... search done
copying images... [100%] ../../cats.gif
copying static files... done
copying extra files... done
dumping search index in English (code: en)... done
dumping object inventory... done
build succeeded, 1 warning.

The HTML pages are in build/html.
```


### Requirements

An environment to build the documentation will need certain libraries installed
to work and produce the right output. These are listed under the `docs` section
in `pyproject.toml` and can be installed in a virtual environment as follows:
```shell
python3 -m venv .venv
source .venv/bin/activate
pip install '.[docs]'
```
