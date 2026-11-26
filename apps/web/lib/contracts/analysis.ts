import { z } from "zod/v4";

export const RequirementSchema = z.strictObject({
  text: z.string(),
  type: z.enum(["must", "nice"]),
  category: z.enum(["technical", "soft", "tool", "domain", "logistics"]),
});

const KeywordSchema = z.strictObject({
  term: z.string(),
  kind: z.enum(["technical", "soft", "tool", "domain"]),
});

export const PostingAnalysisSchema = z.strictObject({
  jdLang: z.enum(["en", "es", "other"]),
  companyName: z.string().nullable(),
  roleTitle: z.string().nullable(),
  seniority: z.enum(["junior", "mid", "senior", "lead"]).nullable(),
  requirements: z.array(RequirementSchema),
  keywords: z.array(KeywordSchema),
  redFlags: z.array(z.string()),
});

export const AnalysisSchema = PostingAnalysisSchema.extend({
  keywords: z.array(KeywordSchema.extend({ presentInProfile: z.boolean() })),
  matchScore: z.number().min(0).max(100),
});

export type Requirement = z.infer<typeof RequirementSchema>;
export type PostingAnalysis = z.infer<typeof PostingAnalysisSchema>;
export type Analysis = z.infer<typeof AnalysisSchema>;
