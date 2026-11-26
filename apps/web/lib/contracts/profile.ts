import { z } from "zod/v4";

export const FactSchema = z.object({
  id: z.string().uuid(),
  kind: z.enum(["experience", "project", "skill", "education", "certification", "metric"]),
  text: z.string().min(1).max(500),
  metrics: z.array(z.string()).default([]),
  provenance: z.enum(["cv_upload", "user_input", "chat_answer"]),
});

export const ExperienceSchema = z.object({
  company: z.string().min(1),
  role: z.string().min(1),
  startDate: z.string().nullable(),
  endDate: z.string().nullable(),
  bullets: z.array(z.string()),
});

export const ProfileSchema = z.object({
  name: z.string().min(1),
  contact: z.object({
    phone: z.string().optional(),
    email: z.string().email(),
    linkedin: z.string().url().optional(),
    github: z.string().url().optional(),
    city: z.string().optional(),
  }),
  languages: z.array(z.object({ lang: z.string(), level: z.string() })),
  experience: z.array(ExperienceSchema),
  projects: z.array(z.object({
    name: z.string(),
    stack: z.string().optional(),
    url: z.string().url().optional(),
    bullets: z.array(z.string()),
  })),
  skills: z.array(z.string()),
  education: z.array(z.object({ degree: z.string(), institution: z.string() })),
  certifications: z.array(z.string()),
});

export type Fact = z.infer<typeof FactSchema>;
export type Experience = z.infer<typeof ExperienceSchema>;
export type Profile = z.infer<typeof ProfileSchema>;
