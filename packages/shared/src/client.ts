// Thin client for the Rails API (api/app/controllers/api/v1). Used by the extension and the web app.
import type {
  ArgumentMapPayload,
  AttemptResponse,
  DeviceResponse,
  ErrorLogCapture,
  ErrorLogEntry,
  ErrorLogPage,
  GenerationResponse,
  GenerationRunState,
  FeedPage,
  Item,
  MapChallenge,
  Me,
  FeedbackResponse,
  FlagReason,
  MapResponse,
} from "./api";
import type { Difficulty, QuestionType } from "./types";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
  ) {
    super(`API ${status}: ${code}`);
  }
}

export interface GenerationRequest {
  url: string;
  title: string;
  text: string;
  selection?: string;
  types: QuestionType[];
  difficulty: Difficulty;
  count_per_type: number;
}

export class ApiClient {
  constructor(
    readonly baseUrl: string,
    private token: string | null = null,
    private fetchImpl: typeof fetch = (...args) => fetch(...args),
  ) {}

  setToken(token: string) {
    this.token = token;
  }

  registerDevice(): Promise<DeviceResponse> {
    return this.request("POST", "/api/v1/devices");
  }

  generate(body: GenerationRequest): Promise<GenerationResponse> {
    return this.request("POST", "/api/v1/generations", body);
  }

  createMap(body: Pick<GenerationRequest, "url" | "title" | "text" | "selection">): Promise<MapResponse> {
    return this.request("POST", "/api/v1/maps", body);
  }

  getMap(id: number): Promise<ArgumentMapPayload> {
    return this.request("GET", `/api/v1/maps/${id}`);
  }

  answerChallenge(mapId: number, index: number, choice: string): Promise<MapChallenge> {
    return this.request("POST", `/api/v1/maps/${mapId}/challenges/${index}/answer`, { choice });
  }

  getRun(id: number): Promise<GenerationRunState> {
    return this.request("GET", `/api/v1/generations/${id}`);
  }

  listItems(params: { family?: string; before?: string } = {}): Promise<FeedPage> {
    const query = new URLSearchParams(Object.entries(params).filter(([, v]) => v) as [string, string][]).toString();
    return this.request("GET", `/api/v1/items${query ? `?${query}` : ""}`);
  }

  getMe(): Promise<Me> {
    return this.request("GET", "/api/v1/me");
  }

  /** Photo capture is US-only and 13+; the answer says whether the error log is now available. */
  setEligibility(country: string, age13Plus: boolean): Promise<{ country: string; error_log: boolean }> {
    return this.request("POST", "/api/v1/me/eligibility", { country, age_13_plus: age13Plus });
  }

  listErrorLog(): Promise<ErrorLogPage> {
    return this.request("GET", "/api/v1/error_log");
  }

  getErrorLogEntry(id: number): Promise<ErrorLogEntry> {
    return this.request("GET", `/api/v1/error_log/${id}`);
  }

  captureErrorLog(body: ErrorLogCapture): Promise<{ status: "queued"; run_id: number }> {
    return this.request("POST", "/api/v1/error_log", body);
  }

  getItem(id: string): Promise<Item> {
    return this.request("GET", `/api/v1/items/${encodeURIComponent(id)}`);
  }

  attempt(id: string, label: string, timeMs?: number): Promise<AttemptResponse> {
    return this.request("POST", `/api/v1/items/${encodeURIComponent(id)}/attempts`, { label, time_ms: timeMs });
  }

  feedback(id: string, body: { kind: "up" | "down" | "flag"; reason?: FlagReason; comment?: string }): Promise<FeedbackResponse> {
    return this.request("POST", `/api/v1/items/${encodeURIComponent(id)}/feedback`, body);
  }

  /** WebSocket URL for Action Cable, authenticated by the same bearer token. */
  cableUrl(): string {
    const ws = this.baseUrl.replace(/^http/, "ws").replace(/\/+$/, "");
    return `${ws}/cable?token=${encodeURIComponent(this.token ?? "")}`;
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    const res = await this.fetchImpl(`${this.baseUrl.replace(/\/+$/, "")}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new ApiError(res.status, typeof data.error === "string" ? data.error : res.statusText);
    return data as T;
  }
}
