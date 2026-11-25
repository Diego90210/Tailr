import { describe, expect, it } from "vitest";
import { FactSchema, ProfileSchema, type Profile } from "./profile";

const profile: Profile = {
  name: "Test Candidate",
  contact: { email: "candidate@example.com" },
  languages: [],
  experience: [{ company: "Example", role: "Developer", startDate: "2024", endDate: null, bullets: [] }],
  projects: [],
  skills: [],
  education: [],
  certifications: [],
};

const fact = {
  id: "00000000-0000-4000-8000-000000000001",
  kind: "skill",
  text: "TypeScript",
  provenance: "user_input",
};

describe("profile contracts", () => {
  it("accepts optional contact fields and a current role", () => {
    expect(ProfileSchema.parse(profile)).toEqual(profile);
  });

  it("rejects malformed contact details", () => {
    expect(ProfileSchema.safeParse({ ...profile, contact: { email: "not-an-email" } }).success).toBe(false);
  });

  it("defaults fact metrics and rejects invalid IDs, provenance, and oversized text", () => {
    expect(FactSchema.parse(fact)).toEqual({ ...fact, metrics: [] });
    for (const override of [{ id: "not-a-uuid" }, { provenance: "generated" }, { text: "x".repeat(501) }]) {
      expect(FactSchema.safeParse({ ...fact, ...override }).success).toBe(false);
    }
  });
});
