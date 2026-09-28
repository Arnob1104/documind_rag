# DocuMind — Frontend

Next.js 13 (App Router) + Tailwind + shadcn/ui.

This app has **no backend of its own**. It talks to two things:

- **Supabase Auth** (`@supabase/supabase-js`) for sign-up / sign-in. The session's access token is read in `lib/api.ts`.
- **The FastAPI backend** (`../backend`) for everything else, sending `Authorization: Bearer <token>` on each request.

```bash
cp .env.example .env.local   # fill in Supabase URL/anon key + API URL
npm install
npm run dev                  # http://localhost:3000
```

| Path | Purpose |
|---|---|
| `lib/supabase.ts` | Supabase client (auth only) |
| `lib/api.ts` | Typed FastAPI client; maps `snake_case` API rows to the `camelCase` types in `lib/types.ts` |
| `components/auth-provider.tsx` | `useAuth()` session context and `useRequireAuth()` route guard |
| `app/chat/page.tsx` | RAG agent chat UI (sessions, tool-action badges, cited sources) |

Scripts: `npm run dev`, `npm run build`, `npm run typecheck`.
