// =============================================================================
// Tool card — renders expandable tool call/result pairs (S4-D2)
// =============================================================================

import {
	CheckCircle2,
	ChevronDown,
	CircleDashed,
	Loader2,
	TerminalSquare,
} from "lucide-react";
import React from "react";
import {
	Collapsible,
	CollapsibleContent,
	CollapsibleTrigger,
} from "./ui/Collapsible";

interface ToolCardProps {
	name: string;
	state: "running" | "complete" | "error";
	callId: string;
	argumentsText?: string;
	result?: string | null;
}

export default function ToolCard({
	name,
	state,
	callId,
	argumentsText,
	result,
}: ToolCardProps) {
	const formattedArguments = formatStructuredText(argumentsText);
	const formattedResult = formatStructuredText(result);

	return (
		<Collapsible
			defaultOpen={state === "running"}
			className="mb-4 overflow-hidden rounded-xl border bg-muted/20"
		>
			<CollapsibleTrigger className="group flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm transition hover:bg-accent/60">
				{state === "running" ? (
					<span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
						<Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
					</span>
				) : state === "complete" ? (
					<span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[hsl(var(--success)/0.12)] text-[hsl(var(--success))]">
						<CheckCircle2 className="h-4 w-4" aria-hidden="true" />
					</span>
				) : (
					<span className="flex h-8 w-8 items-center justify-center rounded-lg bg-destructive/10 text-destructive">
						<CircleDashed className="h-4 w-4" aria-hidden="true" />
					</span>
				)}
				<span className="min-w-0 flex-1">
					<span className="block truncate font-medium text-foreground">
						{name}
					</span>
					<span className="block text-xs text-muted-foreground">
						{state === "running"
							? "Querying governed commerce data…"
							: "Governed tool evidence available"}
					</span>
				</span>
				<ChevronDown
					className="h-4 w-4 text-muted-foreground transition-transform group-data-[state=open]:rotate-180"
					aria-hidden="true"
				/>
			</CollapsibleTrigger>
			<CollapsibleContent className="border-t bg-background/70 px-3 pb-3 pt-3 text-xs text-muted-foreground">
				<div className="flex items-center justify-between gap-2">
					<span className="inline-flex items-center gap-1.5 font-medium text-foreground">
						<TerminalSquare className="h-3.5 w-3.5" aria-hidden="true" />
						Tool provenance
					</span>
					<code className="rounded-md bg-muted px-1.5 py-0.5">
						{callId.slice(0, 8)}…
					</code>
				</div>
				{formattedArguments && (
					<div className="mt-3">
						<p className="mb-1.5 font-medium text-foreground">Arguments</p>
						<pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded-lg bg-muted p-3 font-mono leading-5">
							{formattedArguments}
						</pre>
					</div>
				)}
				{formattedResult && (
					<div className="mt-3">
						<p className="mb-1.5 font-medium text-foreground">Result</p>
						<pre className="max-h-52 overflow-auto whitespace-pre-wrap rounded-lg bg-muted p-3 font-mono leading-5">
							{formattedResult}
						</pre>
					</div>
				)}
				{state === "running" && (
					<div className="mt-3 flex items-center gap-2 text-primary">
						<Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
						<span>Waiting for the governed result…</span>
					</div>
				)}
			</CollapsibleContent>
		</Collapsible>
	);
}

function formatStructuredText(value?: string | null): string | null {
	if (!value) return null;
	try {
		return JSON.stringify(JSON.parse(value), null, 2);
	} catch {
		return value;
	}
}
