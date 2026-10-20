// TR-SEC-1: posting and CV text are data. Callers wrap them with these
// delimiters; the matching prompt states that content inside is never an
// instruction. The wrapper must also stop the text from closing its delimiter.

export const UNTRUSTED_TAGS = [
  "job_posting",
  "cv_text",
  "target_role",
  "profile_facts",
  "keywords",
  "requirements",
  "facts",
  "coverage",
  "bullets",
] as const;

export type UntrustedTag = (typeof UNTRUSTED_TAGS)[number];

// Any prompt delimiter can be closed, not only the wrapper's own, so neutralise
// every one. Opening tags cannot break out of a block and stay readable.
const CLOSING_TAG = new RegExp(`<\\s*\\/\\s*(${UNTRUSTED_TAGS.join("|")})\\b[^>]*>`, "gi");

function neutralizeClosingTags(text: string): string {
  return text.replace(CLOSING_TAG, "&lt;/$1&gt;");
}

export function wrapUntrusted(tag: UntrustedTag, content: string): string {
  return `<${tag}>\n${neutralizeClosingTags(content)}\n</${tag}>`;
}
