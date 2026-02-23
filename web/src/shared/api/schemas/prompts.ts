import { z } from "zod";

export const promptSummarySchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  prompt: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const promptDetailSchema = promptSummarySchema;

export const promptCreateInputSchema = z.object({
  name: z.string().min(1).max(40),
  description: z.string().max(180).default(""),
  prompt: z.string().min(1).max(20000),
});

export const promptUpdateInputSchema = z.object({
  name: z.string().min(1).max(40).optional(),
  description: z.string().max(180).optional(),
  prompt: z.string().min(1).max(20000).optional(),
});

export type PromptSummary = z.infer<typeof promptSummarySchema>;
export type PromptDetail = z.infer<typeof promptDetailSchema>;
export type PromptCreateInput = z.infer<typeof promptCreateInputSchema>;
export type PromptUpdateInput = z.infer<typeof promptUpdateInputSchema>;
