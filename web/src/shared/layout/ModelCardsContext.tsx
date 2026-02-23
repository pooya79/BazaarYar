"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  activateModelCard,
  getModelCards,
} from "@/shared/api/clients/settings.client";
import type { ModelCard } from "@/shared/api/schemas/settings";

type ModelCardsContextValue = {
  items: ModelCard[];
  activeModelId: string | null;
  defaultModelId: string | null;
  selectedModelId: string | null;
  isLoading: boolean;
  error: string | null;
  refreshModels: (signal?: AbortSignal) => Promise<void>;
  setActiveModel: (modelId: string) => Promise<boolean>;
};

const ModelCardsContext = createContext<ModelCardsContextValue | null>(null);

function parseErrorMessage(error: unknown, fallback: string) {
  if (error && typeof error === "object" && "message" in error) {
    const message = (error as { message?: unknown }).message;
    if (typeof message === "string" && message.trim()) {
      return message;
    }
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return fallback;
}

type ModelCardsProviderProps = {
  children: ReactNode;
};

export function ModelCardsProvider({ children }: ModelCardsProviderProps) {
  const [items, setItems] = useState<ModelCard[]>([]);
  const [activeModelId, setActiveModelId] = useState<string | null>(null);
  const [defaultModelId, setDefaultModelId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const applyPayload = useCallback(
    (payload: {
      items: ModelCard[];
      active_model_id: string | null;
      default_model_id: string | null;
    }) => {
      setItems(payload.items);
      setActiveModelId(payload.active_model_id);
      setDefaultModelId(payload.default_model_id);
    },
    [],
  );

  const refreshModels = useCallback(
    async (signal?: AbortSignal) => {
      setIsLoading(true);
      setError(null);
      try {
        const payload = await getModelCards(signal);
        applyPayload(payload);
      } catch (nextError) {
        if (signal?.aborted) {
          return;
        }
        setError(parseErrorMessage(nextError, "Failed to load model cards."));
      } finally {
        setIsLoading(false);
      }
    },
    [applyPayload],
  );

  useEffect(() => {
    const controller = new AbortController();
    void refreshModels(controller.signal);
    return () => controller.abort();
  }, [refreshModels]);

  useEffect(() => {
    const onRefresh = () => {
      void refreshModels();
    };
    window.addEventListener("model-cards:refresh", onRefresh);
    return () => {
      window.removeEventListener("model-cards:refresh", onRefresh);
    };
  }, [refreshModels]);

  const setActiveModel = useCallback(
    async (modelId: string) => {
      setError(null);
      try {
        const payload = await activateModelCard(modelId);
        applyPayload(payload);
        return true;
      } catch (nextError) {
        setError(
          parseErrorMessage(nextError, "Failed to update active model."),
        );
        return false;
      }
    },
    [applyPayload],
  );

  const selectedModelId = useMemo(() => {
    if (activeModelId) {
      return activeModelId;
    }
    if (defaultModelId) {
      return defaultModelId;
    }
    return items[0]?.id ?? null;
  }, [activeModelId, defaultModelId, items]);

  const value = useMemo<ModelCardsContextValue>(
    () => ({
      items,
      activeModelId,
      defaultModelId,
      selectedModelId,
      isLoading,
      error,
      refreshModels,
      setActiveModel,
    }),
    [
      items,
      activeModelId,
      defaultModelId,
      selectedModelId,
      isLoading,
      error,
      refreshModels,
      setActiveModel,
    ],
  );

  return (
    <ModelCardsContext.Provider value={value}>
      {children}
    </ModelCardsContext.Provider>
  );
}

export function useModelCards() {
  const value = useContext(ModelCardsContext);
  if (!value) {
    throw new Error("useModelCards must be used inside ModelCardsProvider");
  }
  return value;
}
