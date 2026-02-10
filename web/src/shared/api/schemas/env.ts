import { z } from "zod";

const optionalUrlSchema = z.preprocess((value) => {
  if (typeof value !== "string") {
    return value;
  }
  const normalized = value.trim();
  return normalized === "" ? undefined : normalized;
}, z.url().optional());

const envSchema = z.object({
  NEXT_PUBLIC_API_BASE_URL: z.url(),
  NEXT_PUBLIC_PHOENIX_URL: optionalUrlSchema,
});

export const env = envSchema.parse({
  NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
  NEXT_PUBLIC_PHOENIX_URL: process.env.NEXT_PUBLIC_PHOENIX_URL,
});
