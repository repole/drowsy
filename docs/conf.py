# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys
from collections import OrderedDict
root_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, root_path)
import drowsy

project = 'Drowsy'
copyright = '2025, Nicholas Repole'
author = 'Nicholas Repole'
# The short X.Y version.
version = ".".join(drowsy.__version__.split(".")[0:2])
# The full version, including alpha/beta/rc tags.
release = drowsy.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc', 
    'sphinx.ext.intersphinx', 
    'sphinx.ext.coverage', 
    'sphinx.ext.viewcode', 
]
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# autodoc options
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# autosummary options
autosummary_generate = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'

html_theme_options = {
    "logo": "drowsy-logo.png",
    "description_font_style": "italic",
    "description": "GraphQL type features in a REST API",
    "code_font_size": "0.8em",
    "warn_bg": "#FFC",
    "warn_border": "#EEE",
    "github_user": 'repole',
    "github_repo": 'drowsy',
    "fixed_sidebar": True,
    "extra_nav_links": OrderedDict(
        [
            ("drowsy @ PyPI", "https://pypi.python.org/pypi/drowsy"),
            ("drowsy @ GitHub", "https://github.com/repole/drowsy"),
            ("Issue Tracker", "https://github.com/repole/drowsy/issues"),
        ]
    ),
}
html_static_path = ['_static']


intersphinx_mapping = {
    'python': ('http://python.readthedocs.org/en/latest/', None),
}
