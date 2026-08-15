"""Background (Celery) task package for the market research agent.

We use the ``worker`` package name (instead of ``tasks``) on purpose:
the project already has a root ``tasks.py`` module that ``flow.py`` and
``main.py`` import from, and a ``tasks/`` directory would shadow that
module's imports.
"""