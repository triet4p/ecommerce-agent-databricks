// =============================================================================
// Sidebar — conversation list with create/rename/delete (S4-D6, S4-D8)
// =============================================================================

import type { ConversationSummary } from "@ecommerce-agent/core";
import {
	MessageSquare,
	Pencil,
	Plus,
	ShoppingBag,
	Sparkles,
	Trash2,
} from "lucide-react";
import React, { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "./ui/Button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "./ui/Dialog";
import { Input } from "./ui/Input";
import { Separator } from "./ui/Separator";

interface SidebarProps {
	conversations: ConversationSummary[];
	isLoading: boolean;
	onCreate: () => void;
	onRename: (id: string, title: string) => void;
	onDelete: (id: string) => void;
	isOpen: boolean;
	onClose?: () => void;
}

export default function Sidebar({
	conversations,
	isLoading,
	onCreate,
	onRename,
	onDelete,
	isOpen,
	onClose,
}: SidebarProps) {
	const navigate = useNavigate();
	const { conversationId } = useParams();
	const [renameTarget, setRenameTarget] = useState<ConversationSummary | null>(
		null,
	);
	const [renameValue, setRenameValue] = useState("");
	const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

	if (!isOpen) return null;

	return (
		<>
			<button
				type="button"
				className="fixed inset-0 z-30 bg-foreground/15 backdrop-blur-[1px] md:hidden"
				onClick={onClose}
				aria-label="Close sidebar"
			/>
			<aside
				className="fixed inset-y-0 left-0 z-40 flex h-full w-72 flex-col border-r bg-background shadow-2xl md:relative md:z-auto md:shadow-none"
				aria-label="Conversations sidebar"
			>
				{/* Header */}
				<div className="p-4">
					<div className="mb-5 flex items-center gap-3">
						<div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
							<ShoppingBag className="h-5 w-5" aria-hidden="true" />
						</div>
						<div>
							<div className="flex items-center gap-1.5">
								<h2 className="font-semibold">Commerce Agent</h2>
								<Sparkles
									className="h-3.5 w-3.5 text-primary"
									aria-hidden="true"
								/>
							</div>
							<p className="text-xs text-muted-foreground">
								Governed customer support
							</p>
						</div>
					</div>
					<Button
						variant="outline"
						onClick={onCreate}
						aria-label="New conversation"
						className="w-full justify-start rounded-xl border-dashed"
					>
						<Plus className="mr-2 h-4 w-4" aria-hidden="true" />
						New conversation
					</Button>
				</div>

				<Separator />

				{/* Conversation list */}
				<div className="px-4 pb-1 pt-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
					Recent
				</div>
				<ul className="flex-1 overflow-y-auto p-2">
					{isLoading && (
						<li className="space-y-2 p-2" aria-label="Loading conversations">
							<div className="stream-skeleton h-10 rounded-xl" />
							<div className="stream-skeleton h-10 rounded-xl" />
						</li>
					)}

					{!isLoading && conversations.length === 0 && (
						<li className="p-4 text-center text-sm text-muted-foreground">
							No conversations yet.
						</li>
					)}

					{conversations.map((conv) => (
						<li
							key={conv.id}
							className={`group flex items-center gap-1 rounded-xl px-2 py-1.5 text-sm transition hover:bg-accent ${
								conv.id === conversationId
									? "bg-primary/10 font-medium text-foreground"
									: ""
							}`}
						>
							<button
								type="button"
								onClick={() => {
									navigate(`/c/${conv.id}`);
									if (window.innerWidth < 768) onClose?.();
								}}
								className="flex min-w-0 flex-1 items-center gap-2 rounded-lg px-1 py-1.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
							>
								<MessageSquare
									className={`h-4 w-4 shrink-0 ${
										conv.id === conversationId
											? "text-primary"
											: "text-muted-foreground"
									}`}
									aria-hidden="true"
								/>
								<span className="flex-1 truncate">{conv.title}</span>
							</button>

							{/* Actions */}
							<div className="flex shrink-0 gap-0.5 opacity-100 transition md:opacity-0 md:group-focus-within:opacity-100 md:group-hover:opacity-100">
								<button
									type="button"
									onClick={(e) => {
										e.stopPropagation();
										setRenameTarget(conv);
										setRenameValue(conv.title);
									}}
									className="rounded-lg p-1.5 text-muted-foreground transition hover:bg-background hover:text-foreground focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
									aria-label={`Rename ${conv.title}`}
								>
									<Pencil className="h-3.5 w-3.5" aria-hidden="true" />
								</button>
								<button
									type="button"
									onClick={(e) => {
										e.stopPropagation();
										setDeleteTarget(conv.id);
									}}
									className="rounded-lg p-1.5 text-muted-foreground transition hover:bg-destructive/10 hover:text-destructive focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
									aria-label={`Delete ${conv.title}`}
								>
									<Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
								</button>
							</div>
						</li>
					))}
				</ul>

				<Separator />

				<div className="p-4 text-xs leading-5 text-muted-foreground">
					<p className="font-medium text-foreground">Databricks App</p>
					<p>Responses use the governed Agent App and approved tools.</p>
				</div>

				{/* Rename dialog */}
				{renameTarget && (
					<Dialog
						open={!!renameTarget}
						onOpenChange={() => setRenameTarget(null)}
					>
						<DialogContent>
							<DialogHeader>
								<DialogTitle>Rename conversation</DialogTitle>
								<DialogDescription className="mt-1 text-sm text-muted-foreground">
									Use a short title that makes this support thread easy to find.
								</DialogDescription>
							</DialogHeader>
							<form
								onSubmit={(e) => {
									e.preventDefault();
									if (renameTarget && renameValue.trim()) {
										onRename(renameTarget.id, renameValue.trim());
										setRenameTarget(null);
									}
								}}
								className="flex gap-2"
							>
								<Input
									value={renameValue}
									onChange={(e) => setRenameValue(e.target.value)}
									autoFocus
									aria-label="New conversation title"
								/>
								<Button type="submit" size="sm">
									Save
								</Button>
							</form>
						</DialogContent>
					</Dialog>
				)}

				{/* Delete confirm dialog */}
				{deleteTarget && (
					<Dialog
						open={!!deleteTarget}
						onOpenChange={() => setDeleteTarget(null)}
					>
						<DialogContent>
							<DialogHeader>
								<DialogTitle>Delete conversation?</DialogTitle>
								<DialogDescription className="mt-1 text-sm text-muted-foreground">
									This removes the thread from your history.
								</DialogDescription>
							</DialogHeader>
							<p className="mb-4 text-sm text-muted-foreground">
								This conversation will be deleted. This action cannot be undone.
							</p>
							<div className="flex justify-end gap-2">
								<Button variant="outline" onClick={() => setDeleteTarget(null)}>
									Cancel
								</Button>
								<Button
									variant="destructive"
									onClick={() => {
										onDelete(deleteTarget);
										setDeleteTarget(null);
									}}
								>
									Delete
								</Button>
							</div>
						</DialogContent>
					</Dialog>
				)}
			</aside>
		</>
	);
}
