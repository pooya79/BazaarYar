import { z } from "zod";

export const attachmentMediaTypeSchema = z.enum([
  "image",
  "pdf",
  "text",
  "spreadsheet",
  "binary",
]);

export const uploadedAttachmentSchema = z.object({
  id: z.string(),
  filename: z.string(),
  content_type: z.string(),
  media_type: attachmentMediaTypeSchema,
  size_bytes: z.number().int().nonnegative(),
  preview_text: z.string().nullable().optional(),
  extraction_note: z.string().nullable().optional(),
});

export const uploadAttachmentsResponseSchema = z.object({
  files: z.array(uploadedAttachmentSchema),
});

export const textDeltaSchema = z.object({
  type: z.literal("text_delta"),
  content: z.string(),
});

export const reasoningDeltaSchema = z.object({
  type: z.literal("reasoning_delta"),
  content: z.string(),
});

export const toolCallDeltaSchema = z.object({
  type: z.literal("tool_call_delta"),
  id: z.string().nullable().optional(),
  name: z.string().nullable().optional(),
  args: z.string().nullable().optional(),
  index: z.number().int().nullable().optional(),
});

export const toolCallSchema = z.object({
  type: z.literal("tool_call"),
  id: z.string().nullable().optional(),
  name: z.string().nullable().optional(),
  args: z.record(z.string(), z.unknown()).default({}),
  call_type: z.string().nullable().optional(),
});

export const toolResultSchema = z.object({
  type: z.literal("tool_result"),
  tool_call_id: z.string().nullable().optional(),
  content: z.string(),
});

export const finalSchema = z.object({
  type: z.literal("final"),
  output_text: z.string(),
  usage: z.record(z.string(), z.unknown()).nullable().optional(),
  response_metadata: z.record(z.string(), z.unknown()).nullable().optional(),
});

export const streamEventSchema = z.discriminatedUnion("type", [
  textDeltaSchema,
  reasoningDeltaSchema,
  toolCallDeltaSchema,
  toolCallSchema,
  toolResultSchema,
  finalSchema,
]);
