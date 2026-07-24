// =============================================================================
// Hook for conversation CRUD operations (S4-D6)
// =============================================================================

import { useCallback, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useChatContext } from "../contexts/ChatContext";
import {
	createConversation as apiCreate,
	deleteConversation as apiDelete,
	getConversation as apiGet,
	updateConversation as apiUpdate,
	listConversations,
} from "../lib/api";

export function useConversations() {
	const { state, dispatch } = useChatContext();
	const navigate = useNavigate();
	const { conversationId } = useParams();

	// Load conversation list
	const loadConversations = useCallback(async () => {
		dispatch({
			type: "SET_LOADING",
			payload: { key: "conversations", value: true },
		});
		dispatch({ type: "SET_ERROR", payload: null });
		try {
			const list = await listConversations();
			dispatch({ type: "SET_CONVERSATIONS", payload: list });
		} catch (err: unknown) {
			const msg =
				err instanceof Error ? err.message : "Failed to load conversations";
			dispatch({ type: "SET_ERROR", payload: msg });
		} finally {
			dispatch({
				type: "SET_LOADING",
				payload: { key: "conversations", value: false },
			});
		}
	}, [dispatch]);

	// Load single conversation with items
	const loadConversation = useCallback(
		async (id: string) => {
			dispatch({ type: "SET_CURRENT_CONVERSATION", payload: null });
			dispatch({
				type: "SET_LOADING",
				payload: { key: "conversation", value: true },
			});
			dispatch({ type: "SET_ERROR", payload: null });
			try {
				const data = await apiGet(id);
				dispatch({
					type: "SET_CURRENT_CONVERSATION",
					payload: { ...data.conversation, items: data.items },
				});
			} catch (err: unknown) {
				const msg =
					err instanceof Error ? err.message : "Failed to load conversation";
				dispatch({ type: "SET_ERROR", payload: msg });
			} finally {
				dispatch({
					type: "SET_LOADING",
					payload: { key: "conversation", value: false },
				});
			}
		},
		[dispatch],
	);

	// Create new conversation
	const createNew = useCallback(async () => {
		try {
			const conv = await apiCreate();
			dispatch({
				type: "ADD_CONVERSATION",
				payload: {
					id: conv.id,
					title: conv.title,
					created_at: conv.created_at,
					updated_at: conv.updated_at,
				},
			});
			navigate(`/c/${conv.id}`);
			return conv;
		} catch (err: unknown) {
			const msg =
				err instanceof Error ? err.message : "Failed to create conversation";
			dispatch({ type: "SET_ERROR", payload: msg });
			return null;
		}
	}, [dispatch, navigate]);

	// Rename conversation
	const rename = useCallback(
		async (id: string, title: string) => {
			try {
				await apiUpdate(id, title);
				dispatch({ type: "UPDATE_CONVERSATION", payload: { id, title } });
			} catch (err: unknown) {
				const msg =
					err instanceof Error ? err.message : "Failed to rename conversation";
				dispatch({ type: "SET_ERROR", payload: msg });
			}
		},
		[dispatch],
	);

	// Delete conversation
	const remove = useCallback(
		async (id: string) => {
			try {
				await apiDelete(id);
				dispatch({ type: "REMOVE_CONVERSATION", payload: id });
				if (id === conversationId) {
					navigate("/");
				}
			} catch (err: unknown) {
				const msg =
					err instanceof Error ? err.message : "Failed to delete conversation";
				dispatch({ type: "SET_ERROR", payload: msg });
			}
		},
		[conversationId, dispatch, navigate],
	);

	// Load on mount
	useEffect(() => {
		loadConversations();
	}, [loadConversations]);

	return {
		conversations: state.conversations,
		currentConversation: state.currentConversation,
		isLoadingConversations: state.isLoadingConversations,
		isLoadingConversation: state.isLoadingConversation,
		error: state.error,
		loadConversations,
		loadConversation,
		createNew,
		rename,
		remove,
	};
}
