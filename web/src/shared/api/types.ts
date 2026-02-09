import type { z } from "zod";

import type { streamEventSchema } from "./schemas/agent";

export type StreamEvent = z.infer<typeof streamEventSchema>;

export type ApiError = {
  status: number;
  message: string;
  details?: unknown;
};
