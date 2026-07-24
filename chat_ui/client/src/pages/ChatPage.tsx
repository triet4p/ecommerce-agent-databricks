// =============================================================================
// Main chat page — responsive layout with sidebar and message area (S4-D1, D4-D10)
// =============================================================================

import type { WhoAmIResponse } from "@ecommerce-agent/core";
import {
	Bug,
	CircleAlert,
	Menu,
	ShieldCheck,
	ShoppingBag,
	Sparkles,
	UserRound,
} from "lucide-react";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import Composer from "../components/Composer";
import ConversationWelcome from "../components/ConversationWelcome";
import Message from "../components/Message";
import Sidebar from "../components/Sidebar";
import { Button } from "../components/ui/Button";
import { useChat } from "../hooks/useChat";
import { useConversations } from "../hooks/useConversations";
import { getCurrentUser } from "../lib/api";

export function deriveConversationTitle(
	message: string,
	maxLength = 52,
): string {
	const normalized = message.replace(/\s+/g, " ").trim();
	if (normalized.length <= maxLength) return normalized;
	return `${normalized.slice(0, maxLength - 1).trimEnd()}…`;
}

export default function ChatPage() {
	const { conversationId } = useParams();
	const {
		conversations,
		currentConversation,
		isLoadingConversation,
		error,
		loadConversation,
		createNew,
		rename,
		remove,
	} = useConversations();
	const persistedItems =
		currentConversation && currentConversation.id === conversationId
			? currentConversation.items
			: undefined;
	const { messages, streamState, sendMessage, stop, retry } = useChat(
		conversationId ?? null,
		persistedItems,
	);
	const [sidebarOpen, setSidebarOpen] = useState(() =>
		typeof window.matchMedia === "function"
			? window.matchMedia("(min-width: 768px)").matches
			: true,
	);
	const [showDebug, setShowDebug] = useState(false);
	const [currentUser, setCurrentUser] = useState<WhoAmIResponse | null>(null);
	const scrollAnchorRef = useRef<HTMLDivElement | null>(null);
	const developerControlsEnabled = ["localhost", "127.0.0.1"].includes(
		window.location.hostname,
	);
	const visibleTraceId =
		streamState.traceId ??
		[...messages]
			.reverse()
			.find((message) => message.persistedStreamState?.traceId)
			?.persistedStreamState?.traceId ??
		null;

	// Load conversation on route change
	useEffect(() => {
		if (conversationId) {
			loadConversation(conversationId);
		}
	}, [conversationId, loadConversation]);

	useEffect(() => {
		void getCurrentUser()
			.then(setCurrentUser)
			.catch(() => setCurrentUser(null));
	}, []);

	useEffect(() => {
		void conversationId;
		if (window.innerWidth < 768) setSidebarOpen(false);
	}, [conversationId]);

	useEffect(() => {
		void messages.length;
		void streamState.text;
		void streamState.pendingTools.size;
		void streamState.completedTools.size;
		scrollAnchorRef.current?.scrollIntoView?.({
			block: "end",
			behavior: streamState.isStreaming ? "smooth" : "auto",
		});
	}, [
		messages.length,
		streamState.text,
		streamState.isStreaming,
		streamState.pendingTools.size,
		streamState.completedTools.size,
	]);

	// Handle new conversation
	const handleNewConversation = async () => {
		await createNew();
	};

	const handleSendMessage = useCallback(
		(message: string) => {
			if (conversationId && currentConversation?.title === "New conversation") {
				void rename(conversationId, deriveConversationTitle(message));
			}
			void sendMessage(message);
		},
		[conversationId, currentConversation?.title, rename, sendMessage],
	);

	// Handle retry of last message
	const handleRetry = () => {
		const lastUserMsg = messages.filter((m) => m.role === "user").pop();
		if (lastUserMsg) {
			retry(lastUserMsg.content);
		}
	};

	// Keyboard shortcut: Ctrl+Backslash toggles sidebar
	useEffect(() => {
		const handler = (e: KeyboardEvent) => {
			if (e.ctrlKey && e.key === "\\") {
				e.preventDefault();
				setSidebarOpen((v) => !v);
			}
		};
		window.addEventListener("keydown", handler);
		return () => window.removeEventListener("keydown", handler);
	}, []);

	return (
		<div className="flex h-dvh overflow-hidden bg-background">
			{/* Sidebar */}
			<Sidebar
				conversations={conversations}
				isLoading={isLoadingConversation}
				onCreate={handleNewConversation}
				onRename={rename}
				onDelete={remove}
				isOpen={sidebarOpen}
				onClose={() => setSidebarOpen(false)}
			/>

			{/* Main area */}
			<div className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
				{/* Header */}
				<header className="z-20 flex min-h-16 items-center justify-between border-b bg-background/90 px-3 py-2 backdrop-blur sm:px-5">
					<div className="flex min-w-0 items-center gap-2.5">
						<Button
							variant="ghost"
							size="icon"
							onClick={() => setSidebarOpen((v) => !v)}
							aria-label="Toggle sidebar"
							className="shrink-0 rounded-xl"
						>
							<Menu className="h-5 w-5" aria-hidden="true" />
						</Button>
						<div className="min-w-0">
							<h1 className="truncate text-sm font-semibold sm:text-base">
								{currentConversation?.title ?? "E-commerce Support Agent"}
							</h1>
							<div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
								<span className="h-1.5 w-1.5 rounded-full bg-[hsl(var(--success))]" />
								<span>Agent and conversation store connected</span>
							</div>
						</div>
					</div>
					<div className="flex items-center gap-1.5">
						<div
							className="hidden max-w-52 items-center gap-1.5 rounded-full border bg-muted/40 px-2.5 py-1 text-xs text-muted-foreground sm:flex"
							title={currentUser?.user ?? "Authenticated Databricks user"}
						>
							<UserRound className="h-3.5 w-3.5" aria-hidden="true" />
							<span className="truncate">
								{currentUser?.user ?? "Signed in"}
							</span>
						</div>
						{developerControlsEnabled && (
							<Button
								variant="ghost"
								size="icon"
								onClick={() => setShowDebug((v) => !v)}
								aria-label="Toggle debug info"
								className="rounded-xl"
							>
								<Bug className="h-4 w-4" aria-hidden="true" />
							</Button>
						)}
					</div>
				</header>

				{/* Debug panel (S4-D10) */}
				{showDebug && (
					<div className="border-b border-border bg-muted/30 px-4 py-2 text-xs text-muted-foreground">
						<div className="flex flex-wrap gap-4">
							<span>
								Conversation:{" "}
								{conversationId ? `${conversationId.slice(0, 8)}...` : "none"}
							</span>
							<span>
								Stream: {streamState?.isStreaming ? "active" : "idle"}
							</span>
							<span>Tools pending: {streamState?.pendingTools.size ?? 0}</span>
							<span>Tools done: {streamState?.completedTools.size ?? 0}</span>
							<span>Trace: {visibleTraceId ?? "not available"}</span>
						</div>
					</div>
				)}

				{/* Error banner */}
				{error && (
					<div
						className="mx-3 mt-3 flex items-center gap-2 rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive sm:mx-6"
						role="alert"
					>
						<CircleAlert className="h-4 w-4 shrink-0" aria-hidden="true" />
						<span>{error}</span>
					</div>
				)}

				{/* Empty state (S4-D7) */}
				{!conversationId && (
					<div className="assistant-canvas flex flex-1 items-center justify-center overflow-y-auto p-6">
						<div className="max-w-xl text-center">
							<div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/20">
								<ShoppingBag className="h-7 w-7" aria-hidden="true" />
							</div>
							<p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-primary">
								E-commerce support, upgraded
							</p>
							<h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
								Answers grounded in your commerce data.
							</h2>
							<p className="mx-auto mb-6 mt-3 max-w-lg leading-6 text-muted-foreground">
								Start a private thread to investigate orders, delivery, refunds,
								policies, and seller performance.
							</p>
							<Button
								onClick={handleNewConversation}
								size="lg"
								className="rounded-xl shadow-sm"
							>
								<Sparkles className="mr-2 h-4 w-4" aria-hidden="true" />
								Start a conversation
							</Button>
							<div className="mt-5 flex items-center justify-center gap-2 text-xs text-muted-foreground">
								<ShieldCheck
									className="h-4 w-4 text-primary"
									aria-hidden="true"
								/>
								<span>Owner-scoped history and governed tool access</span>
							</div>
						</div>
					</div>
				)}

				{/* Loading state (S4-D7) */}
				{conversationId && isLoadingConversation && (
					<div className="assistant-canvas flex flex-1 justify-center overflow-hidden px-4 py-10 sm:px-6">
						<div className="w-full max-w-4xl space-y-5">
							<div className="stream-skeleton h-24 w-3/4 rounded-2xl" />
							<div className="ml-auto stream-skeleton h-16 w-1/2 rounded-2xl" />
							<div className="stream-skeleton h-32 w-full rounded-2xl" />
						</div>
					</div>
				)}

				{/* Messages area (S4-D1) */}
				{conversationId && !isLoadingConversation && (
					<div className="assistant-canvas flex-1 overflow-y-auto px-3 py-5 sm:px-6 sm:py-8">
						{messages.length === 0 && currentConversation ? (
							<ConversationWelcome onSelect={handleSendMessage} />
						) : (
							<div className="mx-auto flex max-w-4xl flex-col gap-6">
								{messages.map((msg, i) => (
									<Message
										key={msg.id}
										messageRole={msg.role}
										content={msg.content}
										streamState={
											i === messages.length - 1 && msg.role === "assistant"
												? streamState
												: msg.persistedStreamState
										}
									/>
								))}

								{/* Retry on error (S4-D5) */}
								{streamState?.hasError && (
									<div className="flex justify-center">
										<Button
											variant="outline"
											onClick={handleRetry}
											aria-label="Retry"
											className="rounded-xl"
										>
											Retry response
										</Button>
									</div>
								)}

								{/* Scroll anchor */}
								<div id="scroll-anchor" ref={scrollAnchorRef} />
							</div>
						)}
					</div>
				)}

				{/* Unavailable backend state (S4-D7) */}
				{conversationId && !isLoadingConversation && !currentConversation && (
					<div className="assistant-canvas flex flex-1 items-center justify-center p-6">
						<div className="max-w-sm rounded-2xl border bg-background p-6 text-center shadow-sm">
							<CircleAlert className="mx-auto mb-3 h-6 w-6 text-muted-foreground" />
							<p className="font-medium text-foreground">
								Conversation not available
							</p>
							<p className="mt-1 text-sm text-muted-foreground">
								It may have been deleted or is not available to this account.
							</p>
							<Button
								variant="outline"
								className="mt-4 rounded-xl"
								onClick={handleNewConversation}
							>
								Start a new conversation
							</Button>
						</div>
					</div>
				)}

				{/* Composer (S4-D1, S4-D4) */}
				{conversationId && (
					<Composer
						onSend={handleSendMessage}
						onStop={stop}
						isStreaming={streamState?.isStreaming ?? false}
						disabled={!currentConversation}
					/>
				)}
			</div>
		</div>
	);
}
