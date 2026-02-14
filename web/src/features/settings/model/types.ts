import type {
  ModelSettingsResponse,
  ReasoningEffort,
} from "@/shared/api/schemas/settings";

export type ModelSettingsDraft = {
  modelName: string;
  baseUrl: string;
  temperature: string;
  reasoningEffort: ReasoningEffort;
  reasoningEnabled: boolean;
  replacementApiKey: string;
  pendingClearKey: boolean;
};

export const emptySettingsDraft: ModelSettingsDraft = {
  modelName: "",
  baseUrl: "",
  temperature: "1",
  reasoningEffort: "medium",
  reasoningEnabled: true,
  replacementApiKey: "",
  pendingClearKey: false,
};

export function toSettingsDraft(
  settings: ModelSettingsResponse,
): ModelSettingsDraft {
  return {
    modelName: settings.model_name,
    baseUrl: settings.base_url,
    temperature: String(settings.temperature),
    reasoningEffort: settings.reasoning_effort,
    reasoningEnabled: settings.reasoning_enabled,
    replacementApiKey: "",
    pendingClearKey: false,
  };
}
