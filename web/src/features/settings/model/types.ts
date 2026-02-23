import type { ModelCard, ReasoningEffort } from "@/shared/api/schemas/settings";

export type ModelCardDraft = {
  displayName: string;
  modelName: string;
  baseUrl: string;
  temperature: string;
  reasoningEffort: ReasoningEffort;
  reasoningEnabled: boolean;
  replacementApiKey: string;
  pendingClearKey: boolean;
};

export const emptyModelCardDraft: ModelCardDraft = {
  displayName: "",
  modelName: "",
  baseUrl: "",
  temperature: "1",
  reasoningEffort: "medium",
  reasoningEnabled: true,
  replacementApiKey: "",
  pendingClearKey: false,
};

export function toModelCardDraft(card: ModelCard): ModelCardDraft {
  return {
    displayName: card.display_name,
    modelName: card.model_name,
    baseUrl: card.base_url,
    temperature: String(card.temperature),
    reasoningEffort: card.reasoning_effort,
    reasoningEnabled: card.reasoning_enabled,
    replacementApiKey: "",
    pendingClearKey: false,
  };
}
