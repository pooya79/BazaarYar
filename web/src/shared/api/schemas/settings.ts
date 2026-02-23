import { z } from "zod";

export const companyProfileSourceSchema = z.enum(["database", "defaults"]);
export const toolSettingsSourceSchema = z.enum(["database", "defaults"]);

export const reasoningEffortSchema = z.enum(["low", "medium", "high"]);

export const modelCardSchema = z.object({
  id: z.string(),
  display_name: z.string(),
  model_name: z.string(),
  base_url: z.string(),
  temperature: z.number().min(0).max(2),
  reasoning_effort: reasoningEffortSchema,
  reasoning_enabled: z.boolean(),
  has_api_key: z.boolean(),
  api_key_preview: z.string().nullable().optional(),
  is_default: z.boolean(),
  is_active: z.boolean(),
});

export const modelCardsResponseSchema = z.object({
  items: z.array(modelCardSchema),
  active_model_id: z.string().nullable(),
  default_model_id: z.string().nullable(),
});

export const modelCardCreateInputSchema = z
  .object({
    display_name: z.string().min(1).max(255),
    model_name: z.string().min(1),
    api_key: z.string().optional(),
    base_url: z.string().optional(),
    temperature: z.number().min(0).max(2).optional(),
    reasoning_effort: reasoningEffortSchema.optional(),
    reasoning_enabled: z.boolean().optional(),
    is_default: z.boolean().optional(),
    is_active: z.boolean().optional(),
  })
  .strict();

export const modelCardPatchInputSchema = modelCardCreateInputSchema
  .partial()
  .strict();

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

export type CompanyProfileSource = z.infer<typeof companyProfileSourceSchema>;
export type ToolSettingsSource = z.infer<typeof toolSettingsSourceSchema>;
export type ReasoningEffort = z.infer<typeof reasoningEffortSchema>;
export type ModelCard = z.infer<typeof modelCardSchema>;
export type ModelCardsResponse = z.infer<typeof modelCardsResponseSchema>;
export type ModelCardCreateInput = z.infer<typeof modelCardCreateInputSchema>;
export type ModelCardPatchInput = z.infer<typeof modelCardPatchInputSchema>;
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
