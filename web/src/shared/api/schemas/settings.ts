import { z } from "zod";

export const modelSettingsSourceSchema = z.enum([
  "database",
  "environment_defaults",
]);
export const companyProfileSourceSchema = z.enum(["database", "defaults"]);
export const toolSettingsSourceSchema = z.enum(["database", "defaults"]);

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

export const companyProfileResponseSchema = z.object({
  name: z.string(),
  description: z.string(),
  enabled: z.boolean(),
  source: companyProfileSourceSchema,
});

export const companyProfilePatchInputSchema = z
  .object({
    name: z.string().max(255).optional(),
    description: z.string().optional(),
    enabled: z.boolean().optional(),
  })
  .strict();

export const resetCompanyProfileResponseSchema = z.object({
  reset: z.boolean(),
});

export const toolCatalogToolSchema = z.object({
  key: z.string(),
  label: z.string(),
  description: z.string(),
  default_enabled: z.boolean(),
  available: z.boolean(),
  unavailable_reason: z.string().nullable().optional(),
  enabled: z.boolean(),
});

export const toolCatalogGroupSchema = z.object({
  key: z.string(),
  label: z.string(),
  enabled: z.boolean(),
  tools: z.array(toolCatalogToolSchema),
});

export const toolSettingsResponseSchema = z.object({
  groups: z.array(toolCatalogGroupSchema),
  tool_overrides: z.record(z.string(), z.boolean()),
  source: toolSettingsSourceSchema,
});

export const toolSettingsPatchInputSchema = z
  .object({
    tool_overrides: z.record(z.string(), z.boolean()),
  })
  .strict();

export const resetToolSettingsResponseSchema = z.object({
  reset: z.boolean(),
});

export type ModelSettingsSource = z.infer<typeof modelSettingsSourceSchema>;
export type CompanyProfileSource = z.infer<typeof companyProfileSourceSchema>;
export type ToolSettingsSource = z.infer<typeof toolSettingsSourceSchema>;
export type ReasoningEffort = z.infer<typeof reasoningEffortSchema>;
export type ModelSettingsResponse = z.infer<typeof modelSettingsResponseSchema>;
export type ModelSettingsPatchInput = z.infer<
  typeof modelSettingsPatchInputSchema
>;
export type CompanyProfileResponse = z.infer<
  typeof companyProfileResponseSchema
>;
export type CompanyProfilePatchInput = z.infer<
  typeof companyProfilePatchInputSchema
>;
export type ToolCatalogTool = z.infer<typeof toolCatalogToolSchema>;
export type ToolCatalogGroup = z.infer<typeof toolCatalogGroupSchema>;
export type ToolSettingsResponse = z.infer<typeof toolSettingsResponseSchema>;
export type ToolSettingsPatchInput = z.infer<
  typeof toolSettingsPatchInputSchema
>;
