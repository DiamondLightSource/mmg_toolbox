"""
Run local instance of docs for testing
Run make_docs.py first
"""

from mkdocs.commands import serve

serve.serve('../mkdocs.yml')
