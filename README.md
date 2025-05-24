# Observability docs

This repo contains docs and scripts for building and deploying documentation for the Canonical Observability Stack.

Docs are [published to readthedocs](https://library.canonical.com/documentation/publish-on-read-the-docs)
and are based on [Canonical's Sphinx Starter Pack](https://github.com/canonical/sphinx-docs-starter-pack).

## Building the docs locally

You must install python3-venv before you can build the documentation, for example

```bash
sudo apt install python3-venv
```

After installing the python3-venv package, (re)create your virtual environment.

```bash
rm -rf docs/.sphinx/venv
python3 -m venv docs/.sphinx/venv
```

and install sphinx dependencies:

```bash
cd docs
source .sphinx/venv/bin/activate
pip install -r .sphinx/requirements.txt
```

Build and serve the docs locally:

```bash
make run
```