# sourmash

[![Documentation](https://readthedocs.org/projects/sourmash/badge/?version=latest)](http://sourmash.readthedocs.io/en/latest/)
[![Build Status](https://travis-ci.com/dib-lab/sourmash.svg?branch=master)](https://travis-ci.com/dib-lab/sourmash)
[![codecov](https://codecov.io/gh/dib-lab/sourmash/branch/master/graph/badge.svg)](https://codecov.io/gh/dib-lab/sourmash)
[![DOI](http://joss.theoj.org/papers/10.21105/joss.00027/status.svg)](http://joss.theoj.org/papers/10.21105/joss.00027)

Compute MinHash signatures for nucleotide (DNA/RNA) and protein sequences.

Usage:

    sourmash compute *.fq.gz
    sourmash compare *.sig -o distances
    sourmash plot distances

Sourmash 1.0 is [published on JOSS](https://doi.org/10.21105/joss.00027); please cite that paper if you use sourmash (`doi: 10.21105/joss.00027`):.

----

The name is a riff off of [Mash](https://github.com/marbl/Mash),
combined with @ctb's love of whiskey.
([Sour mash](https://en.wikipedia.org/wiki/Sour_mash) is used in
making whiskey.)

Primary authors: [C. Titus Brown](mailto:titus@idyll.org) ([@ctb](http://github.com/ctb)) and [Luiz C. Irber, Jr](mailto:sourmash@luizirber.org) ([@luizirber](http://github.com/luizirber)).

sourmash is a product of the
[Lab for Data-Intensive Biology](http://ivory.idyll.org/lab/) at the
[UC Davis School of Veterinary Medicine](http://www.vetmed.ucdavis.edu).

## Installation

We recommend using bioconda to install sourmash:

```
conda install sourmash
```
This will install the latest stable version of sourmash 2.

You can also use pip to install sourmash:

```
pip install sourmash
```

A quickstart tutorial [is available](https://sourmash.readthedocs.io/en/latest/tutorials.html).

### Requirements

sourmash runs under both Python 2.7.x and Python 3.5+.  The base
requirements are screed and ijson, together with a C++ development
environment and the CPython development headers and libraries (for the
C++ extension).

The comparison code (`sourmash compare`) uses numpy, and the plotting
code uses matplotlib and scipy, but most of the code is usable without
these.

For `search` and `gather` you also need `khmer` version 2.1+.

### Installation with conda

Bioconda is a channel for the [conda](http://conda.pydata.org/docs/intro.html) package manager with a focus on bioinformatics software. After installing conda you will need to add the bioconda channel as well as the [other channels](https://bioconda.github.io/index.html#set-up-channels) bioconda depends on. Once you have setup bioconda, you can install sourmash by running:

```bash
$ conda create -n sourmash_env sourmash python=3.6.4
$ source activate sourmash_env
$ sourmash compute -h
```

which will install the latest alpha release.

## Support

Please ask questions and files issues
[on Github](https://github.com/dib-lab/sourmash/issues).

## Development

Development happens on github at
[dib-lab/sourmash](https://github.com/dib-lab/sourmash).

After installation, `sourmash` is the main command-line entry point;
run it with `python -m sourmash`, or do `pip install -e /path/to/repo` to
do a developer install in a virtual environment.

The `sourmash/` directory contains the library code.

Tests require py.test and can be run with `make test`.

Please see [the developer notes](doc/developer.md) for more information.

----

CTB
Dec 2018
