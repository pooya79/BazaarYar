import { buildUrl, normalizeError } from "../http";
import {
  type CompanyProfilePatchInput,
  type CompanyProfileResponse,
  companyProfilePatchInputSchema,
  companyProfileResponseSchema,
  type ModelCardCreateInput,
  type ModelCardPatchInput,
  type ModelCardsResponse,
  modelCardCreateInputSchema,
  modelCardPatchInputSchema,
  modelCardsResponseSchema,
  resetCompanyProfileResponseSchema,
  resetToolSettingsResponseSchema,
  type ToolSettingsPatchInput,
  type ToolSettingsResponse,
  toolSettingsPatchInputSchema,
  toolSettingsResponseSchema,
} from "../schemas/settings";

async function parsePayload(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function getModelCards(
  signal?: AbortSignal,
): Promise<ModelCardsResponse> {
  const response = await fetch(buildUrl("/api/settings/models"), {
    method: "GET",
    signal,
  });
  const payload = await parsePayload(response);
  if (!response.ok) {
    throw normalizeError(response, payload);
  }
  return modelCardsResponseSchema.parse(payload);
}

export async function createModelCard(
  body: ModelCardCreateInput,
  signal?: AbortSignal,
): Promise<ModelCardsResponse> {
  const normalizedBody = modelCardCreateInputSchema.parse(body);
  const response = await fetch(buildUrl("/api/settings/models"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(normalizedBody),
    signal,
  });
  const payload = await parsePayload(response);
  if (!response.ok) {
    throw normalizeError(response, payload);
  }
  return modelCardsResponseSchema.parse(payload);
}

export async function patchModelCard(
  modelId: string,
  body: ModelCardPatchInput,
  signal?: AbortSignal,
): Promise<ModelCardsResponse> {
  const normalizedBody = modelCardPatchInputSchema.parse(body);
  const response = await fetch(buildUrl(`/api/settings/models/${modelId}`), {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(normalizedBody),
    signal,
  });
  const payload = await parsePayload(response);
  if (!response.ok) {
    throw normalizeError(response, payload);
  }
  return modelCardsResponseSchema.parse(payload);
}

export async function deleteModelCard(
  modelId: string,
  signal?: AbortSignal,
): Promise<ModelCardsResponse> {
  const response = await fetch(buildUrl(`/api/settings/models/${modelId}`), {
    method: "DELETE",
    signal,
  });
  const payload = await parsePayload(response);
  if (!response.ok) {
    throw normalizeError(response, payload);
  }
  return modelCardsResponseSchema.parse(payload);
}

export async function activateModelCard(
  modelId: string,
  signal?: AbortSignal,
): Promise<ModelCardsResponse> {
  const response = await fetch(
    buildUrl(`/api/settings/models/${modelId}/activate`),
    {
      method: "POST",
      signal,
    },
  );
  const payload = await parsePayload(response);
  if (!response.ok) {
    throw normalizeError(response, payload);
  }
  return modelCardsResponseSchema.parse(payload);
}

export async function setDefaultModelCard(
  modelId: string,
  signal?: AbortSignal,
): Promise<ModelCardsResponse> {
  const response = await fetch(
    buildUrl(`/api/settings/models/${modelId}/default`),
    {
      method: "POST",
      signal,
    },
  );
  const payload = await parsePayload(response);
  if (!response.ok) {
    throw normalizeError(response, payload);
  }
  return modelCardsResponseSchema.parse(payload);
}

export async function getCompanyProfile(
  signal?: AbortSignal,
): Promise<CompanyProfileResponse> {
  const response = await fetch(buildUrl("/api/settings/company"), {
    method: "GET",
    signal,
  });
  const payload = await parsePayload(response);
  if (!response.ok) {
    throw normalizeError(response, payload);
  }
  return companyProfileResponseSchema.parse(payload);
}

export async function patchCompanyProfile(
  body: CompanyProfilePatchInput,
  signal?: AbortSignal,
): Promise<CompanyProfileResponse> {
  const normalizedBody = companyProfilePatchInputSchema.parse(body);
  const response = await fetch(buildUrl("/api/settings/company"), {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(normalizedBody),
    signal,
  });
  const payload = await parsePayload(response);
  if (!response.ok) {
    throw normalizeError(response, payload);
  }
  return companyProfileResponseSchema.parse(payload);
}

export async function resetCompanyProfile(
  signal?: AbortSignal,
): Promise<boolean> {
  const response = await fetch(buildUrl("/api/settings/company"), {
    method: "DELETE",
    signal,
  });
  const payload = await parsePayload(response);
  if (!response.ok) {
    throw normalizeError(response, payload);
  }
  return resetCompanyProfileResponseSchema.parse(payload).reset;
}

export async function getToolSettings(
  signal?: AbortSignal,
): Promise<ToolSettingsResponse> {
  const response = await fetch(buildUrl("/api/settings/tools"), {
    method: "GET",
    signal,
  });
  const payload = await parsePayload(response);
  if (!response.ok) {
    throw normalizeError(response, payload);
  }
  return toolSettingsResponseSchema.parse(payload);
}

export async function patchToolSettings(
  body: ToolSettingsPatchInput,
  signal?: AbortSignal,
): Promise<ToolSettingsResponse> {
  const normalizedBody = toolSettingsPatchInputSchema.parse(body);
  const response = await fetch(buildUrl("/api/settings/tools"), {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(normalizedBody),
    signal,
  });
  const payload = await parsePayload(response);
  if (!response.ok) {
    throw normalizeError(response, payload);
  }
  return toolSettingsResponseSchema.parse(payload);
}

export async function resetToolSettings(
  signal?: AbortSignal,
): Promise<boolean> {
  const response = await fetch(buildUrl("/api/settings/tools"), {
    method: "DELETE",
    signal,
  });
  const payload = await parsePayload(response);
  if (!response.ok) {
    throw normalizeError(response, payload);
  }
  return resetToolSettingsResponseSchema.parse(payload).reset;
}
