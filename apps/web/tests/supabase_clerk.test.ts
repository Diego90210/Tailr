import { auth } from "@clerk/nextjs/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createUserSupabaseClient } from "@/lib/supabase";

vi.mock("server-only", () => ({}));
vi.mock("@clerk/nextjs/server", () => ({ auth: vi.fn() }));

const url = "https://supabase.example.test";
const key = "sb_publishable_test_fixture";

function mockSession(userId: string | null, token: string | null) {
  const getToken = vi.fn().mockResolvedValue(token);
  vi.mocked(auth, { partial: true }).mockResolvedValue({ userId, getToken });
  return getToken;
}

describe("Clerk-authenticated Supabase client", () => {
  const fetch = vi.fn<typeof globalThis.fetch>();

  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", url);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", key);
    fetch.mockReset().mockImplementation(async () => Response.json([]));
    vi.stubGlobal("fetch", fetch);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("uses each request's default Clerk session token and the public API key", async () => {
    const tokenA = mockSession("user_a", "session-a");
    const clientA = await createUserSupabaseClient();
    const tokenB = mockSession("user_b", "session-b");
    const clientB = await createUserSupabaseClient();

    for (const [client, getToken, token] of [
      [clientA, tokenA, "session-a"],
      [clientB, tokenB, "session-b"],
    ] as const) {
      const { error } = await client.from("tailr_profiles").select("id");
      expect(error).toBeNull();
      expect(getToken).toHaveBeenCalledExactlyOnceWith();
      const [target, init] = fetch.mock.lastCall!;
      expect(String(target)).toBe(`${url}/rest/v1/tailr_profiles?select=id`);
      expect(new Headers(init?.headers).get("authorization")).toBe(`Bearer ${token}`);
      expect(new Headers(init?.headers).get("apikey")).toBe(key);
    }
  });

  it("fails closed when no Clerk user is signed in", async () => {
    const getToken = mockSession(null, null);
    await expect(createUserSupabaseClient()).rejects.toThrow("Clerk sign-in required");
    expect(getToken).not.toHaveBeenCalled();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("does not make an anonymous request when Clerk returns no token", async () => {
    mockSession("user_a", null);
    await expect(createUserSupabaseClient()).rejects.toThrow("Clerk session token unavailable");
    expect(fetch).not.toHaveBeenCalled();
  });

  it("rejects a non-publishable key before creating a client", async () => {
    mockSession("user_a", "session-a");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "wrong-key-type");
    await expect(createUserSupabaseClient()).rejects.toThrow("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY");
    expect(fetch).not.toHaveBeenCalled();
  });
});
