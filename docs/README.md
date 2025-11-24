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

An environment to build the documentation will need certain libraries
installed to work and produce the right output. The
``docs-requirements.txt`` file in this directory lists those libraries.


#### Environment for building

The documentation can be built (and indeed, has been built) with the
following environment. Note certain libraries will also need to be
installed and aren't available with conda; at present these are:

* the Renku theme, available via `pip install renku-sphinx-theme`.

You can create this precise conda environment via running
`conda create --name <env> --file <below as a file>` on the below stored in
a text file (or piped in, etc.):

```text
# This file may be used to create an environment using:
# $ conda create --name <env> --file <this file>
# platform: linux-64
@EXPLICIT
https://conda.anaconda.org/conda-forge/linux-64/_libgcc_mutex-0.1-conda_forge.tar.bz2
https://conda.anaconda.org/conda-forge/linux-64/ca-certificates-2023.5.7-hbcca054_0.conda
https://conda.anaconda.org/conda-forge/linux-64/ld_impl_linux-64-2.40-h41732ed_0.conda
https://conda.anaconda.org/conda-forge/linux-64/python_abi-3.11-3_cp311.conda
https://conda.anaconda.org/conda-forge/noarch/tzdata-2023c-h71feb2d_0.conda
https://conda.anaconda.org/conda-forge/linux-64/libgomp-13.1.0-he5830b7_0.conda
https://conda.anaconda.org/conda-forge/linux-64/_openmp_mutex-4.5-2_gnu.tar.bz2
https://conda.anaconda.org/conda-forge/linux-64/libgcc-ng-13.1.0-he5830b7_0.conda
https://conda.anaconda.org/conda-forge/linux-64/bzip2-1.0.8-h7f98852_4.tar.bz2
https://conda.anaconda.org/conda-forge/linux-64/libbrotlicommon-1.0.9-h166bdaf_8.tar.bz2
https://conda.anaconda.org/conda-forge/linux-64/libexpat-2.5.0-hcb278e6_1.conda
https://conda.anaconda.org/conda-forge/linux-64/libffi-3.4.2-h7f98852_5.tar.bz2
https://conda.anaconda.org/conda-forge/linux-64/libnsl-2.0.0-h7f98852_0.tar.bz2
https://conda.anaconda.org/conda-forge/linux-64/libuuid-2.38.1-h0b41bf4_0.conda
https://conda.anaconda.org/conda-forge/linux-64/libzlib-1.2.13-h166bdaf_4.tar.bz2
https://conda.anaconda.org/conda-forge/linux-64/ncurses-6.4-hcb278e6_0.conda
https://conda.anaconda.org/conda-forge/linux-64/openssl-3.1.1-hd590300_1.conda
https://conda.anaconda.org/conda-forge/linux-64/xz-5.2.6-h166bdaf_0.tar.bz2
https://conda.anaconda.org/conda-forge/linux-64/libbrotlidec-1.0.9-h166bdaf_8.tar.bz2
https://conda.anaconda.org/conda-forge/linux-64/libbrotlienc-1.0.9-h166bdaf_8.tar.bz2
https://conda.anaconda.org/conda-forge/linux-64/libsqlite-3.42.0-h2797004_0.conda
https://conda.anaconda.org/conda-forge/linux-64/readline-8.2-h8228510_1.conda
https://conda.anaconda.org/conda-forge/linux-64/tk-8.6.12-h27826a3_0.tar.bz2
https://conda.anaconda.org/conda-forge/linux-64/brotli-bin-1.0.9-h166bdaf_8.tar.bz2
https://conda.anaconda.org/conda-forge/linux-64/python-3.11.3-h2755cc3_0_cpython.conda
https://conda.anaconda.org/conda-forge/noarch/alabaster-0.7.13-pyhd8ed1ab_0.conda
https://conda.anaconda.org/conda-forge/linux-64/brotli-1.0.9-h166bdaf_8.tar.bz2
https://conda.anaconda.org/conda-forge/noarch/certifi-2023.5.7-pyhd8ed1ab_0.conda
https://conda.anaconda.org/conda-forge/noarch/charset-normalizer-3.1.0-pyhd8ed1ab_0.conda
https://conda.anaconda.org/conda-forge/noarch/colorama-0.4.6-pyhd8ed1ab_0.tar.bz2
https://conda.anaconda.org/conda-forge/linux-64/docutils-0.20.1-py311h38be061_0.conda
https://conda.anaconda.org/conda-forge/noarch/idna-3.4-pyhd8ed1ab_0.tar.bz2
https://conda.anaconda.org/conda-forge/noarch/imagesize-1.4.1-pyhd8ed1ab_0.tar.bz2
https://conda.anaconda.org/conda-forge/linux-64/markupsafe-2.1.3-py311h459d7ec_0.conda
https://conda.anaconda.org/conda-forge/noarch/packaging-23.1-pyhd8ed1ab_0.conda
https://conda.anaconda.org/conda-forge/noarch/pygments-2.15.1-pyhd8ed1ab_0.conda
https://conda.anaconda.org/conda-forge/noarch/pysocks-1.7.1-pyha2e5f31_6.tar.bz2
https://conda.anaconda.org/conda-forge/noarch/pytz-2023.3-pyhd8ed1ab_0.conda
https://conda.anaconda.org/conda-forge/noarch/setuptools-67.7.2-pyhd8ed1ab_0.conda
https://conda.anaconda.org/conda-forge/noarch/snowballstemmer-2.2.0-pyhd8ed1ab_0.tar.bz2
https://conda.anaconda.org/conda-forge/noarch/sphinxcontrib-applehelp-1.0.4-pyhd8ed1ab_0.conda
https://conda.anaconda.org/conda-forge/noarch/sphinxcontrib-devhelp-1.0.2-py_0.tar.bz2
https://conda.anaconda.org/conda-forge/noarch/sphinxcontrib-htmlhelp-2.0.1-pyhd8ed1ab_0.conda
https://conda.anaconda.org/conda-forge/noarch/sphinxcontrib-jsmath-1.0.1-py_0.tar.bz2
https://conda.anaconda.org/conda-forge/noarch/sphinxcontrib-qthelp-1.0.3-py_0.tar.bz2
https://conda.anaconda.org/conda-forge/noarch/sphinxcontrib-serializinghtml-1.1.5-pyhd8ed1ab_2.tar.bz2
https://conda.anaconda.org/conda-forge/noarch/wheel-0.40.0-pyhd8ed1ab_0.conda
https://conda.anaconda.org/conda-forge/noarch/zipp-3.15.0-pyhd8ed1ab_0.conda
https://conda.anaconda.org/conda-forge/noarch/babel-2.12.1-pyhd8ed1ab_1.conda
https://conda.anaconda.org/conda-forge/noarch/importlib-metadata-6.6.0-pyha770c72_0.conda
https://conda.anaconda.org/conda-forge/noarch/jinja2-3.1.2-pyhd8ed1ab_1.tar.bz2
https://conda.anaconda.org/conda-forge/noarch/pip-23.1.2-pyhd8ed1ab_0.conda
https://conda.anaconda.org/conda-forge/noarch/urllib3-2.0.3-pyhd8ed1ab_0.conda
https://conda.anaconda.org/conda-forge/noarch/requests-2.31.0-pyhd8ed1ab_0.conda
https://conda.anaconda.org/conda-forge/noarch/sphinx-7.0.1-pyhd8ed1ab_0.conda
https://conda.anaconda.org/conda-forge/noarch/sphinx-copybutton-0.5.2-pyhd8ed1ab_0.conda
```
