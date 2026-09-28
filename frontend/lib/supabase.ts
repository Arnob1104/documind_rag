import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!url || !anonKey) {
  console.warn(
    "Missing NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY — copy .env.example to .env.local"
  );
}

// The browser talks to Supabase Auth only. All data goes through the FastAPI backend.
export const supabase = createClient(
  url || "http://localhost:54321",
  anonKey || "missing-anon-key"
);
