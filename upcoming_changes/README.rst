Filing Change Log Entries
=========================

deapi uses `towncrier <https://towncrier.readthedocs.io/>`_ to manage its
changelog.  When you open a pull request that should appear in the next release
notes, add a short news **fragment file** to this directory as part of that PR.

Naming convention
-----------------

Each fragment is a plain ``.rst`` file named::

    {PR_number}.{type}.rst

where ``{PR_number}`` is the GitHub pull-request number and ``{type}`` is one
of the types below.

If a change has no natural PR number (e.g. work batched on a long-lived
feature branch), name the file ``+{slug}.{type}.rst`` — the leading ``+``
marks it as an "orphan" fragment so towncrier omits the issue link. Without
it, the slug is rendered as a broken PR link in the changelog (this bit the
0.2.0 notes).

=================  ==============================================================
Type               Use when …
=================  ==============================================================
``api_change``     Existing behaviour changed in a way a user has to act on —
                   a signature, a default, or a gesture that now does something
                   different.  Use this even when the change is a *fix*: what
                   matters to a reader upgrading is that the old behaviour is
                   gone, and that is easy to miss under ``bugfix``.
``new_feature``    A user-visible capability has been added.
``bugfix``         A bug has been fixed.
``deprecation``    Something is deprecated and will be removed in a future release.
``removal``        A previously deprecated API has been removed.
``doc``            Documentation improved without any code change.
``maintenance``    Internal / infrastructure change invisible to end users.
=================  ==============================================================

Content guidelines
------------------

* **One sentence per file**, written in the **past tense**, from a user's
  perspective.
* Cross-reference the relevant class or function with a Sphinx role where
  it adds value.
* Do **not** include the PR number in the sentence body — towncrier appends
  the link automatically.

Examples
--------

``123.new_feature.rst``::

    Added :meth:`~deapi.Client.get_virtual_image_buffer` for reading virtual
    images while a scan is still running.

``124.bugfix.rst``::

    Fixed :meth:`~deapi.Client.set_binning` failing to set hardware binning to 1.

``125.deprecation.rst``::

    Deprecated ``Client.SetProperty``; use ``client[name] = value`` instead.
    ``SetProperty`` will be removed in a future release.

``126.removal.rst``::

    Removed ``Client.GetImage``, which was deprecated since 5.2.

``127.doc.rst``::

    Added an example that scans a region of interest with an XY array.

``128.maintenance.rst``::

    Moved the test workflow to ``uv``.

Previewing the changelog locally
---------------------------------

See what the next release notes would look like **without** modifying any
files or consuming any fragments::

    uvx towncrier build --draft --version 5.x.0

To actually build the changelog (done automatically by the
**Prepare Release** workflow — do not run this by hand unless you know what
you are doing)::

    uvx towncrier build --yes --version 5.x.0

