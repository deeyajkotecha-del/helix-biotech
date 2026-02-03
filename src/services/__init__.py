"""
Helix Services Module
Ported from Node.js CLI services
"""

from .email_finder import find_email, find_emails_for_kols
from .trial_investigators import search_trial_investigators, TrialInvestigator
from .kol_finder import find_kols, KOL, KOLSearchResult
from .ir_scraper import scrape_ir_documents, IRDocument, IRScraperResult

__all__ = [
    'find_email',
    'find_emails_for_kols',
    'search_trial_investigators',
    'TrialInvestigator',
    'find_kols',
    'KOL',
    'KOLSearchResult',
    'scrape_ir_documents',
    'IRDocument',
    'IRScraperResult',
]
