import { z } from "zod";

export const RequirementSchema = z.object({
  text: z.string(),
  type: z.enum(["must", "nice"]),
  category: z.enum(["technical", "soft", "tool", "domain", "logistics"]),
});

export const AnalysisSchema = z.object({
  jdLang: z.enum(["en", "es", "other"]),
  companyName: z.string().nullable(),
  roleTitle: z.string().nullable(),
  requirements: z.array(RequirementSchema),
  keywords: z.array(z.object({
    term: z.string(),
    kind: z.enum(["technical", "soft", "tool", "domain"]),
    presentInProfile: z.boolean(),
  })),
  matchScore: z.number().min(0).max(100),
  redFlags: z.array(z.string()),
});

export type Requirement = z.infer<typeof RequirementSchema>;
export type Analysis = z.infer<typeof AnalysisSchema>;
