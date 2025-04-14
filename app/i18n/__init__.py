import gettext
import os
from typing import Dict, List, Callable, Any
from fastapi import Request, Depends
from babel.support import Translations
from functools import lru_cache
from gettext import gettext as _  # Ensure `_` is imported for translations

# Define supported languages
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'de': 'Deutsch',
}

DEFAULT_LANGUAGE = 'de'  # Default is German

# Path to translations
LOCALE_DIR = os.path.join(os.path.dirname(__file__), 'locales')

@lru_cache(maxsize=None)
def get_translation(lang_code: str) -> gettext.NullTranslations:
    """
    Load and cache translations for the given language
    """
    translations = gettext.translation(
        'messages', 
        localedir=LOCALE_DIR, 
        languages=[lang_code], 
        fallback=True
    )
    return translations

def get_locale_from_request(request: Request) -> str:
    """
    Determine the best language based on:
    1. URL parameter (e.g., '?lang=de')
    2. User session
    3. Accept-Language header
    4. Default language
    """
    # Check URL parameter
    lang_param = request.query_params.get('lang')
    if lang_param in SUPPORTED_LANGUAGES:
        return lang_param
        
    # Check session
    session = request.session.get('language')
    if session in SUPPORTED_LANGUAGES:
        return session
    
    # Check Accept-Language header
    accept_language = request.headers.get('accept-language', '')
    if accept_language:
        for lang in accept_language.split(','):
            lang_code = lang.split(';')[0].strip().lower()
            lang_code = lang_code.split('-')[0]  # Convert 'en-US' to 'en'
            if lang_code in SUPPORTED_LANGUAGES:
                return lang_code
    
    return DEFAULT_LANGUAGE

def get_translator(locale: str = Depends(get_locale_from_request)):
    """
    Return a FastAPI dependency that provides the translation function
    """
    translations = get_translation(locale)
    gettext_func = translations.gettext
    
    # Make the gettext function available with both _ and gettext names
    return {
        "_": gettext_func,
        "gettext": gettext_func,
        "locale": locale
    }
