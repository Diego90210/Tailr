import { describe, expect, it } from "vitest";
import { AnalysisSchema, PostingAnalysisSchema, type Analysis } from "./analysis";

const analysis: Analysis = {
  jdLang: "other",
  companyName: null,
  roleTitle: null,
  seniority: null,
  requirements: [{ text: "Remote work", type: "must", category: "logistics" }],
  keywords: [{ term: "TypeScript", kind: "tool", presentInProfile: true }],
  matchScore: 100,
  redFlags: [],
};

describe("analysis contract", () => {
  it("accepts unknown company and role, including scores at both bounds", () => {
    expect(AnalysisSchema.parse(analysis)).toEqual(analysis);
    expect(AnalysisSchema.safeParse({ ...analysis, matchScore: 0 }).success).toBe(true);
  });

  it("rejects out-of-range scores and invalid requirement types", () => {
    for (const matchScore of [-1, 101, "50"]) {
      expect(AnalysisSchema.safeParse({ ...analysis, matchScore }).success).toBe(false);
    }
    const requirements = [{ ...analysis.requirements[0], type: "preferred" }];
    expect(AnalysisSchema.safeParse({ ...analysis, requirements }).success).toBe(false);
  });
});

it("rejects app-computed fields in model output", () => {
  const { matchScore, keywords, ...base } = analysis;
  const posting = { ...base, keywords: [{ term: "TypeScript", kind: "technical" }] };
  expect(PostingAnalysisSchema.parse(posting)).toEqual(posting);
  expect(PostingAnalysisSchema.safeParse({ ...posting, matchScore }).success).toBe(false);
  expect(PostingAnalysisSchema.safeParse({ ...posting, keywords }).success).toBe(false);
  expect(PostingAnalysisSchema.safeParse({ ...posting, seniority: "principal" }).success).toBe(false);
});
