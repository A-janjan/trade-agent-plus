"""multi-agent LLM financial trading framework.

Loads `.env` at package import so that DEFAULT_CONFIG's env-var overlay and
every downstream client see the user's keys regardless of entry point. Values
already exported by the caller are never overridden.
"""

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))
