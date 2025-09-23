# Configuration file for the Sphinx documentation app.

# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


import sys
import os
import deapi


# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.append("../")

# Project information
project = "deapi"

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = "_static/de_api_icon.svg"

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.

# html_favicon = "_static/logo.ico"


master_doc = "index"

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    "sphinxcontrib.bibtex",
    "sphinx_design",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.githubpages",
    "sphinx.ext.graphviz",
    "sphinx.ext.mathjax",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.linkcode",
    "sphinx_codeautolink",
    "sphinx_gallery.gen_gallery",
    "sphinx_copybutton",
    "nbsphinx",
]

# Create links to references within deapi's documentation to these packages.
intersphinx_mapping = {
    "dask": ("https://docs.dask.org/en/stable", None),
    "diffpy.structure": ("https://www.diffpy.org/diffpy.structure", None),
    "diffsims": ("https://diffsims.readthedocs.io/en/stable", None),
    "hyperspy": ("https://hyperspy.org/hyperspy-doc/current", None),
    "h5py": ("https://docs.h5py.org/en/stable", None),
    "matplotlib": ("https://matplotlib.org/stable", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "orix": ("https://orix.readthedocs.io/en/stable", None),
    "python": ("https://docs.python.org/3", None),
    "scipy": ("https://docs.scipy.org/doc/scipy", None),
    "skimage": ("https://scikit-image.org/docs/stable", None),
    "sklearn": ("https://scikit-learn.org/stable", None),
    "rosettasciio": ("https://hyperspy.org/rosettasciio/", None),
}


_version = deapi.__version__
version_match = "dev" if "dev" in _version else ".".join(_version.split(".")[:2])


# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files. This image also affects
# html_static_path and html_extra_path.

# The theme to use for HTML and HTML Help pages.  See the documentation for a
# list of builtin themes.
html_theme = "pydata_sphinx_theme"

html_theme_options = {
    "github_url": "https://github.com/directelectron/deapi",
    "header_links_before_dropdown": 7,
    "navigation_with_keys": True,
    "show_toc_level": 2,
    "use_edit_page_button": True,
    "navbar_start": ["navbar-logo"],
}
import os

# -- General HTML configuration ---------------------------------------------

html_context = {
    "github_user": "deapi",
    "github_repo": "deapi",
    "github_version": "main",
    "doc_path": "doc",
}

# Use relative URLs for all pages and assets
html_use_relative_urls = True

# -- HTML static files (CSS/JS) --------------------------------------------
html_static_path = ["_static"]

# Add extra CSS files if needed
html_css_files = [
    "custom.css",  # your custom CSS
]

# -- Dynamic base URL for main vs PR preview --------------------------------
pr_number = os.environ.get("GITHUB_PR_NUMBER")
if pr_number:
    # PR preview URL path
    html_baseurl = (
        f"https://previewde.github.io/deapi-preview/pr-preview/pr-{pr_number}/"
    )
else:
    # Main branch URL
    html_baseurl = "https://directelectron.github.io/deapi/"

# -- Theme and theme options -------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "collapse_navigation": False,
    "sticky_navigation": False,
}

# -- Sphinx-Gallery configuration -------------------------------------------
sphinx_gallery_conf = {
    "backreferences_dir": "reference/generated",
    "doc_module": ("deapi",),
    "examples_dirs": "../examples",
    "gallery_dirs": "examples",
    "filename_pattern": "^((?!sgskip).)*$",
    "ignore_pattern": "_sgskip.py",
    "reference_url": {"deapi": None},
    "show_memory": True,
}

# -- Autodoc and other extensions -------------------------------------------
autodoc_default_options = {"show-inheritance": True}
autosummary_generate = True
graphviz_output_format = "svg"
pygments_style = "friendly"
napoleon_google_docstring = False
napoleon_use_param = False
napoleon_use_ivar = True
nitpicky = True
numfig = True
nbsphinx_execute = "never"
nbsphinx_kernel_name = "python3"
nbsphinx_allow_errors = True
exclude_patterns = ["_build", "**.ipynb_checkpoints", "examples/*/*.ipynb"]
bibtex_bibfiles = ["bibliography.bib"]


# -- Autodoc skip handler ---------------------------------------------------
def autodoc_skip_member(app, what, name, obj, skip, options):
    return False


def setup(app):
    app.connect("autodoc-skip-member", autodoc_skip_member)
