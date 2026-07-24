// =============================================================================
// Message component — renders chat messages with streaming support (S4-D1, S4-B6)
// =============================================================================

import type { StreamState } from "@ecommerce-agent/core";
import { Bot, CircleAlert, Sparkles } from "lucide-react";
import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ToolCard from "./ToolCard";

interface MessageProps {
	messageRole: "user" | "assistant";
	content: string;
	streamState?: StreamState;
}

export default function Message({
	messageRole,
	content,
	streamState,
}: MessageProps) {
	const isUser = messageRole === "user";
	const isStreaming = streamState?.isStreaming;
	const hasError = streamState?.hasError;
	const shouldRenderContent =
		content && !(hasError && content.startsWith("Error:"));

	return (
		<div
			className={`flex w-full gap-3 ${isUser ? "justify-end" : "justify-start"}`}
			role="log"
			aria-label={`${isUser ? "User" : "Assistant"} message`}
		>
			{!isUser && (
				<div className="mt-6 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border bg-background shadow-sm">
					<Bot className="h-4 w-4 text-primary" aria-hidden="true" />
				</div>
			)}
			<div
				className={`min-w-0 ${
					isUser
						? "max-w-[88%] rounded-2xl rounded-br-md bg-primary px-4 py-3 text-primary-foreground shadow-sm sm:max-w-[75%]"
						: "w-full max-w-[calc(100%-2.75rem)]"
				}`}
			>
				{!isUser && (
					<div className="mb-2 flex items-center gap-2 text-xs">
						<span className="font-semibold text-foreground">
							Commerce Agent
						</span>
						<span className="inline-flex items-center gap-1 text-muted-foreground">
							<Sparkles className="h-3 w-3" aria-hidden="true" />
							AI response
						</span>
					</div>
				)}

				<div
					className={
						isUser
							? ""
							: "rounded-2xl rounded-tl-md border bg-background/95 p-4 shadow-sm sm:p-5"
					}
				>
					{/* Tool cards */}
					{streamState && !isUser && (
						<>
							{Array.from(streamState.completedTools.entries()).map(
								([callId, name]) => (
									<ToolCard
										key={callId}
										name={name}
										state="complete"
										callId={callId}
										argumentsText={
											streamState.toolDetails.get(callId)?.arguments
										}
										result={streamState.toolDetails.get(callId)?.result}
									/>
								),
							)}
							{Array.from(streamState.pendingTools.entries()).map(
								([callId, name]) => (
									<ToolCard
										key={callId}
										name={name}
										state="running"
										callId={callId}
										argumentsText={
											streamState.toolDetails.get(callId)?.arguments
										}
										result={streamState.toolDetails.get(callId)?.result}
									/>
								),
							)}
						</>
					)}

					{/* Message text */}
					<div className="streamdown-content break-words">
						{shouldRenderContent ? (
							<ReactMarkdown remarkPlugins={[remarkGfm]}>
								{content}
							</ReactMarkdown>
						) : isStreaming ? (
							<div
								className="space-y-2 py-1"
								aria-label="Assistant is preparing a response"
							>
								<div className="stream-skeleton h-3 w-4/5 rounded-full" />
								<div className="stream-skeleton h-3 w-3/5 rounded-full" />
								<div className="stream-skeleton h-3 w-2/5 rounded-full" />
							</div>
						) : (
							""
						)}
						{content && isStreaming && (
							<span
								className="ml-1 inline-block h-4 w-1 animate-pulse rounded-full bg-primary align-middle"
								aria-hidden="true"
							/>
						)}
					</div>

					{/* Phase label */}
					{streamState &&
						!isUser &&
						streamState.isStreaming &&
						streamState.phaseLabel && (
							<div
								className="mt-3 inline-flex items-center gap-2 rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary"
								aria-live="polite"
							>
								<span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
								{streamState.phaseLabel}
							</div>
						)}

					{/* Error */}
					{hasError && (
						<div className="mt-2 flex gap-2 rounded-xl border border-destructive/20 bg-destructive/5 p-3 text-sm text-destructive">
							<CircleAlert
								className="mt-0.5 h-4 w-4 shrink-0"
								aria-hidden="true"
							/>
							<div>
								<p className="font-medium">The assistant could not finish.</p>
								<p className="mt-0.5 text-xs">{streamState.errorMessage}</p>
							</div>
						</div>
					)}
				</div>

				{!isUser && content && !isStreaming && !hasError && (
					<p className="mt-2 px-1 text-[11px] text-muted-foreground">
						AI-generated from governed commerce data and tools. Verify
						high-impact decisions.
					</p>
				)}
			</div>
		</div>
	);
}
