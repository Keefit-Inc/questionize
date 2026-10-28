// Copy for API errors and live progress events in the side panel.
import { ApiError, type GenerationEvent } from "@questionize/shared";

const ERRORS: Record<string, string> = {
  article_too_short: "Couldn't find enough article text on this page.",
  invalid_url: "Open a regular web article first.",
  daily_limit_reached: "You've reached today's generation limit. Practice the questions you have, or come back tomorrow.",
  unauthorized: "Your session expired. Reopen the panel to reconnect.",
  not_found: "That question no longer exists.",
};

export function errorMessage(error: unknown, server: string): string {
  if (error instanceof ApiError) {
    if (error.status === 429 && error.code !== "daily_limit_reached") return "Slow down a little and try again in a minute.";
    return ERRORS[error.code] ?? `Something went wrong (${error.status}).`;
  }
  if (error instanceof TypeError) return `Can't reach ${server}. Check your connection or the server in Settings.`;
  return error instanceof Error ? error.message : String(error);
}

const AGENTS: Partial<Record<GenerationEvent["stage"], string>> = {
  analyze: "Analyst",
  analyzed: "Analyst",
  plan: "Planner",
  write: "Writer",
  solve: "Solver",
  critic: "Critic",
  judge: "Judge",
  verdict: "Verifier",
  revise: "Reviser",
  error: "Error",
};

export function eventLine(event: GenerationEvent): { who: string; text: string; ok?: boolean } | null {
  if (event.stage === "question" || event.stage === "done") return null;
  const question = "index" in event && typeof event.index === "number" ? ` Q${event.index + 1}` : "";
  const who = `${AGENTS[event.stage] ?? event.stage}${question}`;
  const ok = event.stage === "verdict" ? event.passed : event.stage === "error" || event.stage === "failed" ? false : undefined;
  return { who, text: event.message, ok };
}
