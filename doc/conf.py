# Configuration file for the Sphinx documentation builder.

import os
import pathlib
import importlib.util

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

# -- Options for HTML output -------------------------------------------------
# Ensure pydata-sphinx-theme is available
if importlib.util.find_spec("pydata_sphinx_theme") is None:
    raise RuntimeError("pydata-sphinx-theme is not installed in this environment")

pr_number = os.environ.get("GITHUB_PR_NUMBER")

html_theme = "pydata_sphinx_theme"

if pr_number:
    html_static_path = [f"pr-preview/pr-{pr_number}/_static"]
    html_logo = "pr-preview/pr-{pr_number}/_static/de_api_icon.svg"

else:
    html_static_path = ["_static"]
    html_logo = "_static/de_api_icon.svg"

master_doc = "index"

# --- URL handling for GitHub Pages preview ---------------------------------


# -- Autodoc / Autosummary ---------------------------------------------------
autosummary_ignore_module_all = False
autosummary_imported_members = True
autodoc_typehints_format = "short"
autodoc_default_options = {"show-inheritance": True}
autosummary_generate = True

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


# -- Optional: add custom CSS if present ------------------------------------
def setup(app):
    css_file = "custom.css"
    css_path = pathlib.Path(__file__).parent / "_static" / css_file
    print(f"[DEBUG] Adding CSS: {css_path} → exists? {css_path.exists()}")
    if css_path.exists():
        app.add_css_file(css_file)
    else:
        print("[DEBUG] No custom.css found, skipping.")


# -- Debug prints ------------------------------------------------------------
static_dir = pathlib.Path(__file__).parent / "_static"
print(
    f"[DEBUG] Looking for static folder: {static_dir} → exists? {static_dir.exists()}"
)
print(f"[DEBUG] GITHUB_PR_NUMBER = {pr_number}")
