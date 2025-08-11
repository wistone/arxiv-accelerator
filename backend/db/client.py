import os
from typing import Optional

from supabase import Client, create_client


_supabase_client: Optional[Client] = None


def get_client() -> Client:
    """Create or return a singleton Supabase client using Service Role if available."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    url = os.getenv("SUPABASE_URL")
    # Prefer Service Role for server operations; fall back to ANON if necessary
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_*_KEY in environment")

    _supabase_client = create_client(url, key)
    return _supabase_client


def app_schema():
    """Return a PostgREST client scoped to the 'app' schema."""
    client = get_client()
    return client.postgrest.schema("app")


