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

export const conversationSummarySchema = z.object({
  id: z.string(),
  title: z.string().nullable().optional(),
  starred: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
  message_count: z.number().int().nonnegative(),
  last_message_at: z.string().nullable().optional(),
});

export const conversationAttachmentSchema = z.object({
  id: z.string(),
  filename: z.string(),
  content_type: z.string(),
  media_type: attachmentMediaTypeSchema,
  size_bytes: z.number().int().nonnegative(),
  preview_text: z.string().nullable().optional(),
  extraction_note: z.string().nullable().optional(),
  position: z.number().int().nonnegative(),
  download_url: z.string(),
});

export const conversationMessageSchema = z.object({
  id: z.string(),
  role: z.enum(["user", "assistant"]),
  content: z.string(),
  token_estimate: z.number().int().nonnegative(),
  tokenizer_name: z.string().nullable().optional(),
  message_kind: z.enum([
    "normal",
    "summary",
    "meta",
    "tool_call",
    "tool_result",
  ]),
  archived_at: z.string().nullable().optional(),
  usage_json: z.record(z.string(), z.unknown()).nullable().optional(),
  created_at: z.string(),
  attachments: z.array(conversationAttachmentSchema),
});

export const conversationDetailSchema = z.object({
  id: z.string(),
  title: z.string().nullable().optional(),
  starred: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
  messages: z.array(conversationMessageSchema),
});

export const contextWindowSchema = z.object({
  conversation_id: z.string(),
  max_tokens: z.number().int().nonnegative(),
  target_tokens: z.number().int().nonnegative(),
  keep_last_turns: z.number().int().nonnegative(),
  token_sum: z.number().int().nonnegative(),
  messages: z.array(conversationMessageSchema),
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
  conversation_id: z.string().nullable().optional(),
});

export const streamEventSchema = z.discriminatedUnion("type", [
  textDeltaSchema,
  reasoningDeltaSchema,
  toolCallDeltaSchema,
  toolCallSchema,
  toolResultSchema,
  finalSchema,
]);
