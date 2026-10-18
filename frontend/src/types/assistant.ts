export type BuildStatus = 'incomplete' | 'valid' | 'invalid';

export interface VehicleBuild {
  model: string | null;
  engine: string | null;
  transmission: string | null;
  trim: string | null;
  application: string | null;
  region: string | null;
}

export interface RuleFinding {
  ruleId: string;
  ruleType: 'constraint' | 'recommendation';
  message: string;
}

export interface BuildValidation {
  status: BuildStatus;
  missingFields: string[];
  violations: RuleFinding[];
  recommendations: RuleFinding[];
}

export interface VehicleComparison {
  firstVehicle: string;
  secondVehicle: string;
  efficiencyWinner: string;
  powerWinner: string;
  summary: string;
}

export interface SourceReference {
  documentId: string;
  title: string;
  sourceType: string;
  relevanceScore: number;
  wasCited: boolean;
}

export interface AssistantReply {
  reply: string;
  intent: string;
  activeBuild: VehicleBuild;
  validation: BuildValidation;
  comparison: VehicleComparison | null;
  sources: SourceReference[];
  traceId: string;
  latencyMs: number;
}

export interface ChatTurn {
  role: 'user' | 'assistant';
  content: string;
}

export interface ConversationMessage extends ChatTurn {
  messageId: string;
  assistantReply?: AssistantReply;
}

export interface DocumentHit {
  documentId: string;
  sourceType: string;
  score: number;
  rank: number;
}

export interface RequestTrace {
  traceId: string;
  intent: string | null;
  appliedFilters: Record<string, unknown>;
  candidatesByChannel: Record<string, DocumentHit[]>;
  contextDocuments: DocumentHit[];
  citedSourceIds: string[];
  unknownCitationIds: string[];
  replyParsed: boolean | null;
  estimatedPromptTokens: number | null;
  stageDurationsMs: Record<string, number>;
  totalDurationMs: number;
}

export const EMPTY_VEHICLE_BUILD: VehicleBuild = {
  model: null,
  engine: null,
  transmission: null,
  trim: null,
  application: null,
  region: null,
};
