export const PROMPT_COMMAND_PATTERN = /^[a-z0-9][a-z0-9_-]{1,39}$/;

export const normalizePromptCommandName = (value: string) =>
  value
    .trim()
    .replace(/^\\+/, "")
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9_-]/g, "-")
    .replace(/-+/g, "-")
    .replace(/^[-_]+|[-_]+$/g, "");

export const replaceTrailingPromptCommand = (
  input: string,
  promptText: string,
) => {
  const commandRegex = /\\[a-zA-Z0-9_-]*$/;
  if (!commandRegex.test(input)) {
    return input;
  }
  const sanitizedPrompt = promptText.trim();
  return input.replace(commandRegex, `${sanitizedPrompt} `);
};
