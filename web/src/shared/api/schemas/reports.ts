import { z } from "zod";

export const reportSummarySchema = z.object({
  id: z.string(),
  title: z.string(),
  preview_text: z.string(),
  source_conversation_id: z.string().nullable().optional(),
  enabled_for_agent: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const reportDetailSchema = reportSummarySchema.extend({
  content: z.string(),
});

export const reportCreateInputSchema = z.object({
  title: z.string().min(1).max(255),
  content: z.string().min(1).max(20000),
  preview_text: z.string().max(180).nullable().optional(),
  enabled_for_agent: z.boolean().default(true),
  source_conversation_id: z.string().nullable().optional(),
});

export const reportUpdateInputSchema = z.object({
  title: z.string().min(1).max(255).optional(),
  content: z.string().min(1).max(20000).optional(),
  preview_text: z.string().max(180).optional(),
  enabled_for_agent: z.boolean().optional(),
});

export type ReportSummary = z.infer<typeof reportSummarySchema>;
export type ReportDetail = z.infer<typeof reportDetailSchema>;
export type ReportCreateInput = z.infer<typeof reportCreateInputSchema>;
export type ReportUpdateInput = z.infer<typeof reportUpdateInputSchema>;
