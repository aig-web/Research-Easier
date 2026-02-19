"""Vercel serverless entry point.

Exposes the Flask app as a WSGI handler that Vercel's @vercel/python
runtime can invoke.
"""

from app import app
