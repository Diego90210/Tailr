import { describe, expect, it } from "vitest";
import { GenerateRequestSchema, type GenerateRequest } from "./generation";

const bullet = { text: "Built a dashboard", factIds: ["fact-1"] };
const request: GenerateRequest = {
  formatSpec: { headings: { en: { experience: "Experience" } } },
  content: {
    header: { name: "Test Candidate", contactLine: "candidate@example.com" },
    summary: "",
    experience: [{ company: "Example", role: "Developer", start: "2024", end: "Present", bullets: [bullet] }],
    projects: [{ name: "Example Project", bullets: [bullet] }],
    education: [],
    certifications: [],
    skills: [],
    languages: [],
  },
};

describe("generation request contract", () => {
  it("accepts experience and project bullets with fact references and an omitted locale", () => {
    expect(GenerateRequestSchema.parse(request)).toEqual(request);
  });

  it.each(["experience", "projects"] as const)("rejects unreferenced %s bullets", (section) => {
    for (const factIds of [undefined, [], [""]]) {
      const content = {
        ...request.content,
        [section]: [{ ...request.content[section][0], bullets: [{ ...bullet, factIds }] }],
      };
      expect(GenerateRequestSchema.safeParse({ ...request, content }).success).toBe(false);
    }
  });

  it("rejects unsupported locales and empty format specs", () => {
    expect(GenerateRequestSchema.safeParse({ ...request, locale: "fr" }).success).toBe(false);
    expect(GenerateRequestSchema.safeParse({ ...request, formatSpec: {} }).success).toBe(false);
  });
});
