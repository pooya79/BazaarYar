import { z } from "zod";

export const modelSettingsSourceSchema = z.enum([
  "database",
  "environment_defaults",
]);

export const reasoningEffortSchema = z.enum(["low", "medium", "high"]);

export const modelSettingsResponseSchema = z.object({
  model_name: z.string(),
  base_url: z.string(),
  temperature: z.number().min(0).max(2),
  reasoning_effort: reasoningEffortSchema,
  reasoning_enabled: z.boolean(),
  has_api_key: z.boolean(),
  api_key_preview: z.string().nullable().optional(),
  source: modelSettingsSourceSchema,
});

export const modelSettingsPatchInputSchema = z
  .object({
    model_name: z.string().optional(),
    api_key: z.string().optional(),
    base_url: z.string().optional(),
    temperature: z.number().min(0).max(2).optional(),
    reasoning_effort: reasoningEffortSchema.optional(),
    reasoning_enabled: z.boolean().optional(),
  })
  .strict();

export const resetModelSettingsResponseSchema = z.object({
  reset: z.boolean(),
});

export type ModelSettingsSource = z.infer<typeof modelSettingsSourceSchema>;
export type ReasoningEffort = z.infer<typeof reasoningEffortSchema>;
export type ModelSettingsResponse = z.infer<typeof modelSettingsResponseSchema>;
export type ModelSettingsPatchInput = z.infer<
  typeof modelSettingsPatchInputSchema
>;
