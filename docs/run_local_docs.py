"""
Run local instance of docs for testing
Run make_docs.py first

conda activate mkdocs
cd /path/to/mmg_toolbox
python docs/run_local_docs.py
-or-
cd /path/to/mmg_toolbox
mkdocs serve
"""

from mkdocs.commands import serve

serve.serve('mkdocs.yml')
