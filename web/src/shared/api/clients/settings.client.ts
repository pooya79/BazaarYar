import { buildUrl, normalizeError } from "../http";
import {
  type ModelSettingsPatchInput,
  type ModelSettingsResponse,
  modelSettingsPatchInputSchema,
  modelSettingsResponseSchema,
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
