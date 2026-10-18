import type {
  AssistantReply,
  BuildValidation,
  ChatTurn,
  DocumentHit,
  RequestTrace,
  RuleFinding,
  VehicleBuild,
  VehicleComparison,
} from '../types/assistant';

const API_BASE_PATH = '/api/v1';

interface RuleFindingPayload {
  rule_id: string;
  rule_type: RuleFinding['ruleType'];
  message: string;
}

interface AssistantReplyPayload {
  reply: string;
  intent: string;
  active_build: VehicleBuild;
  validation: {
    status: BuildValidation['status'];
    missing_fields: string[];
    violations: RuleFindingPayload[];
    recommendations: RuleFindingPayload[];
  };
  comparison: {
    first_vehicle: string;
    second_vehicle: string;
    efficiency_winner: string;
    power_winner: string;
    summary: string;
  } | null;
  sources: {
    document_id: string;
    title: string;
    source_type: string;
    relevance_score: number;
    was_cited: boolean;
  }[];
  trace_id: string;
  latency_ms: number;
}

interface DocumentHitPayload {
  document_id: string;
  source_type: string;
  score: number;
  rank: number;
}

interface RequestTracePayload {
  trace_id: string;
  intent: string | null;
  applied_filters: Record<string, unknown>;
  candidates_by_channel: Record<string, DocumentHitPayload[]>;
  context_documents: DocumentHitPayload[];
  cited_source_ids: string[];
  unknown_citation_ids: string[];
  language_model: { reply_parsed: boolean; estimated_prompt_tokens: number } | null;
  stage_durations_ms: Record<string, number>;
  total_duration_ms: number;
}

export class AssistantApiError extends Error {}

async function readJsonResponse<ResponseBody>(response: Response): Promise<ResponseBody> {
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new AssistantApiError(errorBody.detail ?? `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<ResponseBody>;
}

function toRuleFinding(payload: RuleFindingPayload): RuleFinding {
  return { ruleId: payload.rule_id, ruleType: payload.rule_type, message: payload.message };
}

function toVehicleComparison(payload: AssistantReplyPayload['comparison']): VehicleComparison | null {
  if (!payload) return null;
  return {
    firstVehicle: payload.first_vehicle,
    secondVehicle: payload.second_vehicle,
    efficiencyWinner: payload.efficiency_winner,
    powerWinner: payload.power_winner,
    summary: payload.summary,
  };
}

function toAssistantReply(payload: AssistantReplyPayload): AssistantReply {
  return {
    reply: payload.reply,
    intent: payload.intent,
    activeBuild: payload.active_build,
    validation: {
      status: payload.validation.status,
      missingFields: payload.validation.missing_fields,
      violations: payload.validation.violations.map(toRuleFinding),
      recommendations: payload.validation.recommendations.map(toRuleFinding),
    },
    comparison: toVehicleComparison(payload.comparison),
    sources: payload.sources.map((source) => ({
      documentId: source.document_id,
      title: source.title,
      sourceType: source.source_type,
      relevanceScore: source.relevance_score,
      wasCited: source.was_cited,
    })),
    traceId: payload.trace_id,
    latencyMs: payload.latency_ms,
  };
}

function toDocumentHit(payload: DocumentHitPayload): DocumentHit {
  return { documentId: payload.document_id, sourceType: payload.source_type, score: payload.score, rank: payload.rank };
}

function toRequestTrace(payload: RequestTracePayload): RequestTrace {
  return {
    traceId: payload.trace_id,
    intent: payload.intent,
    appliedFilters: payload.applied_filters,
    candidatesByChannel: Object.fromEntries(
      Object.entries(payload.candidates_by_channel).map(([channelName, hits]) => [channelName, hits.map(toDocumentHit)]),
    ),
    contextDocuments: payload.context_documents.map(toDocumentHit),
    citedSourceIds: payload.cited_source_ids,
    unknownCitationIds: payload.unknown_citation_ids,
    replyParsed: payload.language_model?.reply_parsed ?? null,
    estimatedPromptTokens: payload.language_model?.estimated_prompt_tokens ?? null,
    stageDurationsMs: payload.stage_durations_ms,
    totalDurationMs: payload.total_duration_ms,
  };
}

export async function sendChatMessage(request: {
  message: string;
  history: ChatTurn[];
  activeBuild: VehicleBuild;
  sessionId: string;
}): Promise<AssistantReply> {
  const response = await fetch(`${API_BASE_PATH}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: request.message,
      history: request.history,
      active_build: request.activeBuild,
      session_id: request.sessionId,
    }),
  });
  return toAssistantReply(await readJsonResponse<AssistantReplyPayload>(response));
}

export async function fetchRequestTrace(traceId: string): Promise<RequestTrace> {
  const response = await fetch(`${API_BASE_PATH}/traces/${encodeURIComponent(traceId)}`);
  return toRequestTrace(await readJsonResponse<RequestTracePayload>(response));
}

export interface ServiceReadiness {
  status: string;
  indexedDocumentCount: number;
  languageModelName: string;
  languageModelReachable: boolean;
}

export async function fetchServiceReadiness(): Promise<ServiceReadiness> {
  const payload = await readJsonResponse<{
    status: string;
    indexed_document_count: number;
    language_model_name: string;
    language_model_reachable: boolean;
  }>(await fetch(`${API_BASE_PATH}/ready`));
  return {
    status: payload.status,
    indexedDocumentCount: payload.indexed_document_count,
    languageModelName: payload.language_model_name,
    languageModelReachable: payload.language_model_reachable,
  };
}
