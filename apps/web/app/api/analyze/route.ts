import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { auth } from "@clerk/nextjs/server";
import { z } from "zod/v4";
import { PostingAnalysisSchema } from "@/lib/contracts/analysis";
import { getProvider, routeForTask, wrapUntrusted } from "@/lib/llm";
import { createUserSupabaseClient } from "@/lib/supabase";

const MAX_JD_CHARS = 20_000;
// Allow JSON escapes (up to six bytes per UTF-16 unit) plus metadata.
const MAX_BODY_BYTES = 128 * 1024;
const RequestSchema = z.strictObject({
  profileId: z.uuid(),
  jdText: z.string().max(MAX_JD_CHARS).trim().min(1).refine((text) => !text.includes("\0") && text.isWellFormed()),
  sourceUrl: z.string().max(2048).pipe(z.url({ protocol: /^https?$/ }))
    .transform((url) => new URL(url).href).nullish(),
});

function error(status: number, code: string) {
  return Response.json({ error: code }, { status });
}

export async function POST(request: Request) {
  try {
    const { userId } = await auth();
    if (!userId) return error(401, "unauthenticated");
    const mediaType = request.headers.get("content-type")?.split(";")[0]?.trim().toLowerCase();
    if (mediaType !== "application/json") return error(415, "unsupported_media_type");
    if (!request.body) return error(400, "invalid_request");

    let payload: unknown;
    try {
      const decoder = new TextDecoder("utf-8", { fatal: true });
      const reader = request.body.getReader();
      let bytes = 0;
      let body = "";
      try {
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          bytes += value.byteLength;
          if (bytes > MAX_BODY_BYTES) return error(413, "payload_too_large");
          body += decoder.decode(value, { stream: true });
        }
      } finally {
        void reader.cancel().catch(() => {});
      }
      payload = JSON.parse(body + decoder.decode());
    } catch {
      return error(400, "invalid_request");
    }
    const parsed = RequestSchema.safeParse(payload);
    if (!parsed.success) {
      if (parsed.error.issues.some(({ path, code }) => path[0] === "jdText" && code === "too_big")) {
        return error(413, "payload_too_large");
      }
      return error(400, "invalid_request");
    }

    const { profileId, jdText, sourceUrl } = parsed.data;
    const supabase = await createUserSupabaseClient();
    const profile = await supabase.from("tailr_profiles")
      .select("id").eq("id", profileId).eq("user_id", userId).maybeSingle();
    if (profile.error) return error(500, "analysis_failed");
    if (!profile.data) return error(404, "profile_not_found");

    const task = "analyze_jd";
    const system = await readFile("../../prompts/analyze-jd.md", "utf8");
    const { provider } = routeForTask(task);
    const completion = await getProvider(provider).complete({
      task,
      system,
      messages: [{ role: "user", content: wrapUntrusted("job_posting", jdText) }],
      schema: PostingAnalysisSchema,
      maxTokens: 4096,
      temperature: 0,
      locale: "es", // The prompt detects posting language independently of UI locale.
    }).catch(() => null);
    if (!completion) return error(502, "analysis_unavailable");

    const analysis = completion.data;
    // The provider call can outlive the Clerk token used for the profile lookup.
    const writer = await createUserSupabaseClient();
    const saved = await writer.from("tailr_job_analyses").insert({
      profile_id: profile.data.id,
      source_url: sourceUrl ?? null,
      jd_text: jdText,
      jd_hash: createHash("sha256").update(jdText).digest("hex"),
      jd_lang: analysis.jdLang,
      company_name: analysis.companyName,
      role_title: analysis.roleTitle,
      requirements: analysis.requirements,
      keywords: analysis.keywords,
      red_flags: analysis.redFlags,
    }).select("id").single();
    if (saved.error || !saved.data) return error(500, "analysis_failed");

    return Response.json({ analysisId: saved.data.id, ...analysis }, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return error(500, "analysis_failed");
  }
}
