# How to set up a development environment to work with docs

```
cd docs
rm -rf .sphinx/venv
uv venv .sphinx/venv
VIRTUAL_ENV=.sphinx/venv uv pip install -r .sphinx/requirements.txt
make linkcheck VENVDIR=.sphinx/venv
```