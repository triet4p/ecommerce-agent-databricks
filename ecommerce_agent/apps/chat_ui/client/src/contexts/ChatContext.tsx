// =============================================================================
// Conversation state store — keyed by canonical IDs (S4-B5)
// =============================================================================

import type {
	Conversation,
	ConversationItem,
	ConversationSummary,
} from "@ecommerce-agent/core";
import type React from "react";
import {
	type ReactNode,
	createContext,
	useCallback,
	useContext,
	useReducer,
} from "react";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

export interface ChatState {
	/** List of conversation summaries for the sidebar. */
	conversations: ConversationSummary[];
	/** Currently active conversation (full data including items). */
	currentConversation: (Conversation & { items: ConversationItem[] }) | null;
	/** Loading flags. */
	isLoadingConversations: boolean;
	isLoadingConversation: boolean;
	/** Error state. */
	error: string | null;
}

const initialState: ChatState = {
	conversations: [],
	currentConversation: null,
	isLoadingConversations: false,
	isLoadingConversation: false,
	error: null,
};

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

type ChatAction =
	| { type: "SET_CONVERSATIONS"; payload: ConversationSummary[] }
	| {
			type: "SET_CURRENT_CONVERSATION";
			payload: (Conversation & { items: ConversationItem[] }) | null;
	  }
	| { type: "ADD_CONVERSATION"; payload: ConversationSummary }
	| { type: "UPDATE_CONVERSATION"; payload: { id: string; title: string } }
	| { type: "REMOVE_CONVERSATION"; payload: string }
	| {
			type: "SET_LOADING";
			payload: { key: "conversations" | "conversation"; value: boolean };
	  }
	| { type: "SET_ERROR"; payload: string | null };

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------

function chatReducer(state: ChatState, action: ChatAction): ChatState {
	switch (action.type) {
		case "SET_CONVERSATIONS":
			return { ...state, conversations: action.payload };
		case "SET_CURRENT_CONVERSATION":
			return { ...state, currentConversation: action.payload };
		case "ADD_CONVERSATION": {
			const exists = state.conversations.some(
				(c) => c.id === action.payload.id,
			);
			if (exists) return state;
			return {
				...state,
				conversations: [action.payload, ...state.conversations],
			};
		}
		case "UPDATE_CONVERSATION":
			return {
				...state,
				conversations: state.conversations.map((c) =>
					c.id === action.payload.id
						? { ...c, title: action.payload.title }
						: c,
				),
				currentConversation:
					state.currentConversation?.id === action.payload.id
						? { ...state.currentConversation, title: action.payload.title }
						: state.currentConversation,
			};
		case "REMOVE_CONVERSATION":
			return {
				...state,
				conversations: state.conversations.filter(
					(c) => c.id !== action.payload,
				),
				currentConversation:
					state.currentConversation?.id === action.payload
						? null
						: state.currentConversation,
			};
		case "SET_LOADING":
			return {
				...state,
				...(action.payload.key === "conversations"
					? { isLoadingConversations: action.payload.value }
					: { isLoadingConversation: action.payload.value }),
			};
		case "SET_ERROR":
			return { ...state, error: action.payload };
		default:
			return state;
	}
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

interface ChatContextValue {
	state: ChatState;
	dispatch: React.Dispatch<ChatAction>;
}

const ChatContext = createContext<ChatContextValue | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function ChatProvider({ children }: { children: ReactNode }) {
	const [state, dispatch] = useReducer(chatReducer, initialState);

	return (
		<ChatContext.Provider value={{ state, dispatch }}>
			{children}
		</ChatContext.Provider>
	);
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useChatContext(): ChatContextValue {
	const ctx = useContext(ChatContext);
	if (!ctx) {
		throw new Error("useChatContext must be used within ChatProvider");
	}
	return ctx;
}
