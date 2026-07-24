// =============================================================================
// Sprint 2 Event Contract — TypeScript types
// =============================================================================

/** Discriminated union for all SSE event types. */
export type SSEEventType =
	| "response.output_text.delta"
	| "response.output_item.done"
	| "response.completed"
	| "error";

export interface SSEEvent {
	type: SSEEventType;
}

// -- Text delta ---------------------------------------------------------------

export interface TextDeltaEvent extends SSEEvent {
	type: "response.output_text.delta";
	item_id: string;
	delta: string;
	content_index: number;
	output_index: number;
}

// -- Output items -------------------------------------------------------------

export type OutputItem =
	| TextMessageOutput
	| FunctionCallOutput
	| FunctionCallResultOutput;

export interface TextMessageOutput {
	type: "message";
	id: string;
	role: "assistant";
	status?: string;
	content: Array<{
		type: "output_text";
		text: string;
		annotations: unknown[];
	}>;
}

export interface FunctionCallOutput {
	type: "function_call";
	id: string;
	call_id: string;
	name: string;
	arguments: string;
}

export interface FunctionCallResultOutput {
	type: "function_call_output";
	call_id: string;
	output: string;
}

// -- OutputItemDoneEvent ------------------------------------------------------

export interface OutputItemDoneEvent extends SSEEvent {
	type: "response.output_item.done";
	item: OutputItem;
	output_index: number;
}

// -- Error event -------------------------------------------------------------

export interface ErrorEvent extends SSEEvent {
	type: "error";
	code: string;
	message: string;
}

// -- Response Completed -------------------------------------------------------

export interface ResponseCompletedEvent extends SSEEvent {
	type: "response.completed";
	response: {
		id: string;
		status: "completed";
		output: OutputItem[];
		trace_id?: string;
	};
}

// -- Union -------------------------------------------------------------------

export type ChatUIStreamEvent =
	| TextDeltaEvent
	| OutputItemDoneEvent
	| ErrorEvent
	| ResponseCompletedEvent;

// =============================================================================
// Sprint 3 Data Model — TypeScript types
// =============================================================================

export interface Conversation {
	id: string;
	owner: string;
	title: string;
	created_at: string;
	updated_at: string;
	deleted_at?: string | null;
}

export interface ConversationSummary {
	id: string;
	title: string;
	created_at: string;
	updated_at: string;
}

export type TurnStatus = "active" | "completed" | "failed" | "cancelled";

export interface Turn {
	id: string;
	conversation_id: string;
	client_request_id: string;
	sequence: number;
	status: TurnStatus;
	mlflow_trace_id?: string | null;
	created_at: string;
	completed_at?: string | null;
}

export type ItemType = "message" | "function_call" | "function_call_output";

export interface ConversationItem {
	id: string;
	conversation_id: string;
	turn_id: string;
	sequence: number;
	item_type: ItemType;
	role?: string | null;
	payload: Record<string, unknown>;
	item_key?: string | null;
	mlflow_trace_id?: string | null;
	created_at: string;
}

/** Response returned when opening a persisted conversation. */
export interface ConversationWithItems {
	conversation: Conversation;
	items: ConversationItem[];
}

// =============================================================================
// Display policy types
// =============================================================================

export const TOOL_DISPLAY_NAMES: Record<string, string> = {
	get_order_status: "🔍 Order lookup",
	get_customer_order_history: "📋 Order history",
	search_policy_docs: "📄 Policy search",
	check_refund_eligibility: "💳 Refund check",
	get_seller_performance: "📊 Seller rating",
	get_shipping_delay_stats: "🚚 Shipping status",
	compute_delay_severity: "⏱ Delay analysis",
	customer_value_score: "⭐ Customer value",
	list_skills: "📚 Available guides",
	load_skill: "📖 Load guide",
};

export function toolDisplayName(name: string): string {
	const canonicalName =
		Object.keys(TOOL_DISPLAY_NAMES).find(
			(knownName) =>
				name === knownName ||
				name.endsWith(`__${knownName}`) ||
				name.endsWith(`.${knownName}`),
		) ?? name;
	return TOOL_DISPLAY_NAMES[canonicalName] ?? `🔧 ${canonicalName}`;
}

export function sanitizeOutput(output: string, maxLength = 1000): string {
	if (output.length > maxLength) {
		return `${output.slice(0, maxLength)}…`;
	}
	return output;
}

export function truncateArguments(args: string, maxLength = 500): string {
	if (args.length > maxLength) {
		return `${args.slice(0, maxLength)}…`;
	}
	return args;
}

// =============================================================================
// Phase label derivation (Sprint 2 §5.2)
// =============================================================================

export interface PhaseFlags {
	hasTextDelta: boolean;
	hasPendingToolCall: boolean;
	hasToolResult: boolean;
	isMultiStep: boolean;
	isError: boolean;
}

export function derivePhaseLabel(flags: PhaseFlags): string {
	if (flags.isError) return "❌ Error";
	if (flags.hasToolResult) return "✅ Tool complete";
	if (flags.isMultiStep) return "🔄 Multi-step…";
	if (flags.hasPendingToolCall && flags.hasTextDelta) return "🔍 Analyzing…";
	if (flags.hasPendingToolCall) return "🔧 Running tool…";
	if (flags.hasTextDelta) return "🤖 Composing…";
	return "";
}

// =============================================================================
// API types
// =============================================================================

export interface ApiError {
	error: {
		code: string;
		message: string;
	};
}

export interface CreateConversationRequest {
	title?: string;
}

export interface UpdateConversationRequest {
	title: string;
}

export interface CreateTurnRequest {
	clientRequestId: string;
	userMessage: string;
}

export interface StreamTurnRequest {
	userMessage: string;
}

export type CancelTurnRequest = Record<string, never>;

export interface HealthResponse {
	healthy: boolean;
	database: boolean;
	agent: boolean;
}

export interface WhoAmIResponse {
	user: string;
	execution_identity: "app_service_principal";
}

// =============================================================================
// Event stream reducer types (S4-B4)
// =============================================================================

export interface StreamState {
	/** Accumulated assistant text. */
	text: string;
	/** Active tool calls keyed by call_id -> display name. */
	pendingTools: Map<string, string>;
	/** Completed tool calls keyed by call_id -> display name. */
	completedTools: Map<string, string>;
	/** Browser-safe details for each correlated tool call/result pair. */
	toolDetails: Map<
		string,
		{ name: string; arguments: string; result: string | null }
	>;
	/** Whether the stream has received an error. */
	hasError: boolean;
	/** Error message if hasError. */
	errorMessage: string | null;
	/** Whether the stream completed successfully. */
	isComplete: boolean;
	/** Derived phase label. */
	phaseLabel: string;
	/** Whether this is currently streaming (in-progress). */
	isStreaming: boolean;
	/** MLflow trace identifier for the completed turn, when available. */
	traceId: string | null;
}

export function createInitialStreamState(isStreaming = true): StreamState {
	return {
		text: "",
		pendingTools: new Map(),
		completedTools: new Map(),
		toolDetails: new Map(),
		hasError: false,
		errorMessage: null,
		isComplete: false,
		phaseLabel: "",
		isStreaming,
		traceId: null,
	};
}

export function reduceStreamEvent(
	state: StreamState,
	event: ChatUIStreamEvent,
): StreamState {
	switch (event.type) {
		case "response.output_text.delta": {
			const next = { ...state, text: state.text + event.delta };
			next.phaseLabel = derivePhaseLabel({
				hasTextDelta: next.text.length > 0,
				hasPendingToolCall: next.pendingTools.size > 0,
				hasToolResult: next.completedTools.size > 0,
				isMultiStep: next.pendingTools.size > 1,
				isError: false,
			});
			return next;
		}

		case "response.output_item.done": {
			const item = event.item;
			const next = { ...state };

			if (item.type === "message") {
				const text = item.content
					.map((b) => ("text" in b ? b.text : ""))
					.join("");
				if (text) next.text = text;
			} else if (item.type === "function_call") {
				const name = toolDisplayName(item.name);
				const newPending = new Map(state.pendingTools);
				newPending.set(item.call_id, name);
				next.pendingTools = newPending;
				const details = new Map(state.toolDetails);
				details.set(item.call_id, {
					name,
					arguments: truncateArguments(item.arguments),
					result: null,
				});
				next.toolDetails = details;
			} else if (item.type === "function_call_output") {
				const newPending = new Map(state.pendingTools);
				const name = newPending.get(item.call_id) ?? "Unknown tool";
				newPending.delete(item.call_id);
				next.pendingTools = newPending;
				const newCompleted = new Map(state.completedTools);
				newCompleted.set(item.call_id, name);
				next.completedTools = newCompleted;
				const details = new Map(state.toolDetails);
				const current = details.get(item.call_id) ?? {
					name,
					arguments: "",
					result: null,
				};
				details.set(item.call_id, {
					...current,
					result: sanitizeOutput(item.output),
				});
				next.toolDetails = details;
			}

			next.phaseLabel = derivePhaseLabel({
				hasTextDelta: next.text.length > 0,
				hasPendingToolCall: next.pendingTools.size > 0,
				hasToolResult: next.completedTools.size > 0,
				isMultiStep: next.pendingTools.size > 1,
				isError: false,
			});
			return next;
		}

		case "response.completed": {
			return {
				...state,
				isComplete: true,
				isStreaming: false,
				traceId: event.response.trace_id ?? event.response.id ?? null,
				phaseLabel: derivePhaseLabel({
					// Completion is terminal; text that was composed earlier must
					// not keep the active "Composing…" phase visible.
					hasTextDelta: false,
					hasPendingToolCall: false,
					hasToolResult: state.completedTools.size > 0,
					isMultiStep: false,
					isError: false,
				}),
			};
		}

		case "error": {
			return {
				...state,
				hasError: true,
				errorMessage: event.message,
				isStreaming: false,
				phaseLabel: derivePhaseLabel({
					hasTextDelta: state.text.length > 0,
					hasPendingToolCall: state.pendingTools.size > 0,
					hasToolResult: state.completedTools.size > 0,
					isMultiStep: false,
					isError: true,
				}),
			};
		}

		default:
			return state;
	}
}
