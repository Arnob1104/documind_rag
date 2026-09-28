from supabase import create_client, Client
from app.config import settings

# Backend uses the SERVICE ROLE key: it bypasses RLS, so every query in this
# codebase must explicitly filter by visibility/ownership itself (see
# services/*.py and routers/*.py) — never assume RLS is protecting a query
# made with this client.
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
