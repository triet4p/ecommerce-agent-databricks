import {
	PackageSearch,
	RotateCcw,
	ShieldCheck,
	Sparkles,
	Truck,
} from "lucide-react";
import type React from "react";

interface ConversationWelcomeProps {
	onSelect: (prompt: string) => void;
}

const STARTERS = [
	{
		icon: PackageSearch,
		title: "Track an order",
		description: "Check status, timing, and delivery progress.",
		prompt: "Help me check the current status of an order.",
	},
	{
		icon: RotateCcw,
		title: "Review a return",
		description: "Understand policy and refund eligibility.",
		prompt: "Explain the return and refund policy for my purchase.",
	},
	{
		icon: Truck,
		title: "Investigate a delay",
		description: "Assess a late shipment and the next best step.",
		prompt: "Help me investigate a delayed delivery.",
	},
] as const;

export default function ConversationWelcome({
	onSelect,
}: ConversationWelcomeProps) {
	return (
		<section className="mx-auto flex w-full max-w-4xl flex-1 flex-col items-center justify-center px-4 py-10 text-center sm:px-8">
			<div className="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl border bg-background shadow-sm">
				<Sparkles className="h-7 w-7 text-primary" aria-hidden="true" />
			</div>
			<p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-primary">
				Governed commerce assistant
			</p>
			<h2 className="max-w-2xl text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
				Resolve order questions with context, not guesswork.
			</h2>
			<p className="mt-3 max-w-xl text-pretty text-sm leading-6 text-muted-foreground sm:text-base">
				Ask naturally. The assistant can use approved order and policy tools,
				then show the evidence behind its answer.
			</p>

			<div className="mt-8 grid w-full gap-3 md:grid-cols-3">
				{STARTERS.map(({ icon: Icon, title, description, prompt }) => (
					<button
						key={title}
						type="button"
						onClick={() => onSelect(prompt)}
						className="group rounded-2xl border bg-background/90 p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
						aria-label={`${title}: ${description}`}
					>
						<span className="mb-4 flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary transition group-hover:bg-primary group-hover:text-primary-foreground">
							<Icon className="h-4 w-4" aria-hidden="true" />
						</span>
						<span className="block font-medium">{title}</span>
						<span className="mt-1 block text-sm leading-5 text-muted-foreground">
							{description}
						</span>
					</button>
				))}
			</div>

			<div className="mt-7 flex items-center gap-2 text-xs text-muted-foreground">
				<ShieldCheck className="h-4 w-4 text-primary" aria-hidden="true" />
				<span>
					Approved tools only · sensitive reasoning is never displayed
				</span>
			</div>
		</section>
	);
}
