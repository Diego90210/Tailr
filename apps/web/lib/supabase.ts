import "server-only";

import { auth } from "@clerk/nextjs/server";
import { createClient } from "@supabase/supabase-js";

export async function createUserSupabaseClient() {
  const { userId, getToken } = await auth();
  if (!userId) throw new Error("Clerk sign-in required");

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY?.trim();
  if (!url || !key?.startsWith("sb_publishable_")) {
    throw new Error("Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY");
  }

  const token = await getToken();
  if (!token) throw new Error("Clerk session token unavailable");
  return createClient(url, key, { accessToken: async () => token });
}
