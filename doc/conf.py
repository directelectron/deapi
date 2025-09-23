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

# -- Options for HTML output -------------------------------------------------
html_theme = "pydata_sphinx_theme"

# Static files (CSS, JS, images)
html_static_path = ["_static"]
html_logo = "_static/de_api_icon.svg"

# Use absolute URLs for PR previews
pr_number = os.environ.get("GITHUB_PR_NUMBER")  # set in workflow
if pr_number:
    html_baseurl = (
        f"https://previewde.github.io/deapi-preview/pr-preview/pr-{pr_number}/"
    )
    html_use_relative_urls = False
else:
    html_baseurl = "https://directelectron.github.io/deapi/"
    html_use_relative_urls = True

master_doc = "index"

# -- Autodoc / Autosummary --------------------------------------------------
autosummary_ignore_module_all = False
autosummary_imported_members = True
autodoc_typehints_format = "short"
autodoc_default_options = {
    "show-inheritance": True,
}
autosummary_generate = True

# -- Sphinx Gallery ---------------------------------------------------------
sphinx_gallery_conf = {
    "examples_dirs": "../examples",
    "gallery_dirs": "examples",
    "filename_pattern": "^((?!sgskip).)*$",
    "ignore_pattern": "_sgskip.py",
    "backreferences_dir": "api",
    "doc_module": ("deapi",),
    "reference_url": {"deapi": None},
}


# -- Optional: add custom CSS if needed ------------------------------------
def setup(app):
    # Automatically include your CSS
    app.add_css_file("custom.css")
