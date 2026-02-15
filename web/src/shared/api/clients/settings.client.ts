import { buildUrl, normalizeError } from "../http";
import {
  type CompanyProfilePatchInput,
  type CompanyProfileResponse,
  companyProfilePatchInputSchema,
  companyProfileResponseSchema,
  type ModelSettingsPatchInput,
  type ModelSettingsResponse,
  modelSettingsPatchInputSchema,
  modelSettingsResponseSchema,
  resetCompanyProfileResponseSchema,
  resetModelSettingsResponseSchema,
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

export async function getModelSettings(
  signal?: AbortSignal,
): Promise<ModelSettingsResponse> {
  const response = await fetch(buildUrl("/api/settings/model"), {
    method: "GET",
    signal,
  });
  const payload = await parsePayload(response);
  if (!response.ok) {
    throw normalizeError(response, payload);
  }
  return modelSettingsResponseSchema.parse(payload);
}

export async function patchModelSettings(
  body: ModelSettingsPatchInput,
  signal?: AbortSignal,
): Promise<ModelSettingsResponse> {
  const normalizedBody = modelSettingsPatchInputSchema.parse(body);
  const response = await fetch(buildUrl("/api/settings/model"), {
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
  return modelSettingsResponseSchema.parse(payload);
}

export async function resetModelSettings(
  signal?: AbortSignal,
): Promise<boolean> {
  const response = await fetch(buildUrl("/api/settings/model"), {
    method: "DELETE",
    signal,
  });
  const payload = await parsePayload(response);
  if (!response.ok) {
    throw normalizeError(response, payload);
  }
  return resetModelSettingsResponseSchema.parse(payload).reset;
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
