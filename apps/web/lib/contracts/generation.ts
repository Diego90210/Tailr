import { z } from "zod";

const BulletSchema = z.object({
  text: z.string(),
  factIds: z.array(z.string().min(1)).min(1),
});

export const GenerateRequestSchema = z.object({
  // The Python renderer owns validation of the format spec fields.
  formatSpec: z.record(z.unknown()).refine((spec) => Object.keys(spec).length > 0),
  locale: z.enum(["en", "es"]).optional(),
  content: z.object({
    header: z.object({ name: z.string().min(1), contactLine: z.string().min(1) }),
    summary: z.string(),
    experience: z.array(z.object({
      company: z.string(),
      role: z.string(),
      start: z.string(),
      end: z.string(),
      bullets: z.array(BulletSchema),
    })),
    projects: z.array(z.object({
      name: z.string(),
      stack: z.string().optional(),
      url: z.string().url().optional(),
      bullets: z.array(BulletSchema),
    })),
    education: z.array(z.string()),
    certifications: z.array(z.string()),
    skills: z.array(z.string()),
    languages: z.array(z.string()),
  }),
});

export type GenerateRequest = z.infer<typeof GenerateRequestSchema>;
