Dev Guide
---------

This section focuses on the development of the deapi. There are some guidelines that should be followed
when contributing to the deapi.  We welcome contributions from the community, especially in the form of
worked examples, tutorials and documentation.  Alternatively, if you have a feature request we would love
to help with developing an implementation.


Formatting:
-----------

- The `deapi` uses the `numpydoc <https://numpydoc.readthedocs.io/en/latest/format.html>`_ style for docstrings.
  This is a standardized format that is used in the scientific Python community.  In order to render the documentation
  correctly, it is important to follow this style.
- The `deapi` uses the `black <https://black.readthedocs.io/en/stable/>`_ code formatter.  The best way to ensure that
  your code is formatted correctly is to use pre-commit hooks.  This can be done by installing the pre-commit package
  and running the following command in the root directory of the `deapi` repository:


.. code-block::

    pre-commit install

Then every time you commit changes to the repository, the pre-commit hooks will run and format the code for you. If
you are having trouble with the pre-commit hooks, GitHub actions will also run the pre-commit hooks for you and
will fail if the code is not formatted correctly.  Then commenting "pre-commit auto-fix" on the pull request will
re-run the pre-commit hooks and fix the formatting for you.

Contributing to the Repository:
--------------------------------

If you would like to contribute to the `deapi`, the best way to do this is to fork the repository.

The General Workflow is as follows:

1. `Fork the repository <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo>`_
    on GitHub.
2. `Clone <https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository>`_
    the forked repository to your local machine.
3. Create a new branch for your changes using the following command:

.. code-block::

    git checkout -b <branch-name>

4. Make your changes to the code.
5. Commit your changes to the branch using the following command:

.. code-block::

    git commit -m "A message describing the changes"

6. Push the changes to the forked repository using the following command:

.. code-block::

    git push origin <branch-name>

7. Create a `pull request <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request>`_
8. The changes will be reviewed by the maintainers and merged into the repository. Note feel free to make a PR early
   if you are unsure about the direction of your changes.  We are happy to help guide you in the right direction!

Testing:
--------
We use pytest for testing the `deapi`.  The tests are located in the `tests` directory.  The tests are run using the
following command:

.. code-block::

    pytest tests/

By default the tests will initialize a python based DEServer on a separate thread. This is done in the
`conftest.py` file using the pytest-xprocess plugin.

If you have a real DEServer running on a different machine, you can run the tests using the following command:

.. code-block::

    pytest tests/ --server

This will run the tests using the DEServer at the specified address and port for the tests using the
default port and host. You can also specify the host and port using the following command:

.. code-block::

    pytest tests/ --server --host <host> --port <port>

This will also run a subset of the tests that require a full DEServer to be running. These tests are marked with the
`@pytest.mark.server` decorator.

Just a note that only one connection to the DEServer will be made.  As the `conftest.py` file runs before every
pytest run this reduces the number of times that the DEServer is started and stopped. It also means that it is
important to make sure that the Client disconnects from the DEServer at the end of the test