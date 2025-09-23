# Configuration file for the Sphinx documentation builder
import os

# -- Project information -----------------------------------------------------
project = "deapi"
copyright = "2024, DE Developers"
author = "DE Developers"
release = "0.1.0"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx_gallery.gen_gallery",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- HTML output options -----------------------------------------------------
html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
html_logo = "_static/de_api_icon.svg"
master_doc = "index"

# -- Base URL for GitHub Pages / PR previews ---------------------------------
pr_number = os.environ.get("GITHUB_PR_NUMBER")  # set in workflow
if pr_number:
    html_baseurl = (
        f"https://previewde.github.io/deapi-preview/pr-preview/pr-{pr_number}/"
    )
else:
    html_baseurl = "https://directelectron.github.io/deapi/"  # main branch

# Use absolute URLs so CSS and static files work in PR previews
html_use_relative_urls = False

# -- Sphinx Gallery ----------------------------------------------------------
sphinx_gallery_conf = {
    "examples_dirs": "../examples",
    "gallery_dirs": "examples",
    "filename_pattern": "^((?!sgskip).)*$",
    "ignore_pattern": "_sgskip.py",
    "backreferences_dir": "api",
    "doc_module": ("deapi",),
    "reference_url": {"deapi": None},
}

# -- Autodoc / Autosummary ---------------------------------------------------
autosummary_generate = True
autosummary_imported_members = True
autosummary_ignore_module_all = False

autodoc_typehints_format = "short"
autodoc_default_options = {
    "show-inheritance": True,
}

# -- Optional: Include custom CSS -------------------------------------------
# If you have a custom CSS file in _static, e.g., _static/custom.css
html_css_files = [
    "custom.css",
]

# -- Optional: Sphinx-Gallery memory logging ---------------------------------
sphinx_gallery_conf["show_memory"] = True

# -- nbsphinx (if using notebooks) -------------------------------------------
nbsphinx_execute = "never"
nbsphinx_kernel_name = "python3"
nbsphinx_allow_errors = True

# -- sphinxcontrib-bibtex ---------------------------------------------------
bibtex_bibfiles = ["bibliography.bib"]


# -- Autodoc skip callback ---------------------------------------------------
def autodoc_skip_member(app, what, name, obj, skip, options):
    # Never skip members
    return False


def setup(app):
    app.connect("autodoc-skip-member", autodoc_skip_member)
