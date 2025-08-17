#!/usr/bin/env python3
"""
Page modules for Modular SQL RAG application.
Contains individual page implementations for the three-page Streamlit app.

Note: This directory is named 'page_modules' instead of 'pages' to prevent
Streamlit's automatic page discovery, which would create duplicate navigation.
"""

# # Export page instances for easy import
# from .search_page import search_page
# from .catalog_page import catalog_page  
# from .chat_page import chat_page

# __all__ = ['search_page', 'catalog_page', 'chat_page']

from modular.page_modules.search_page import search_page
from modular.page_modules.catalog_page import catalog_page
from modular.page_modules.chat_page import chat_page
