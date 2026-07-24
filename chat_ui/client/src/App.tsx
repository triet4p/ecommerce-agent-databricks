// =============================================================================
// Application shell with routing, error boundary, and global layout (S4-B2)
// =============================================================================

import React, { Component, type ReactNode } from "react";
import { Route, Routes } from "react-router-dom";
import { ChatProvider } from "./contexts/ChatContext";
import ChatPage from "./pages/ChatPage";

// ---------------------------------------------------------------------------
// Error boundary
// ---------------------------------------------------------------------------

interface ErrorBoundaryState {
	hasError: boolean;
	error?: Error;
}

class ErrorBoundary extends Component<
	{ children: ReactNode },
	ErrorBoundaryState
> {
	state: ErrorBoundaryState = { hasError: false };

	static getDerivedStateFromError(error: Error): ErrorBoundaryState {
		return { hasError: true, error };
	}

	render() {
		if (this.state.hasError) {
			return (
				<div className="flex h-screen items-center justify-center p-8">
					<div className="max-w-md text-center">
						<h1 className="mb-4 text-2xl font-bold text-destructive">
							Something went wrong
						</h1>
						<p className="mb-4 text-muted-foreground">
							{this.state.error?.message ?? "An unexpected error occurred."}
						</p>
						<button
							type="button"
							onClick={() => window.location.reload()}
							className="rounded bg-primary px-4 py-2 text-primary-foreground hover:opacity-90"
						>
							Reload page
						</button>
					</div>
				</div>
			);
		}
		return this.props.children;
	}
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

export default function App() {
	return (
		<ErrorBoundary>
			<ChatProvider>
				<Routes>
					<Route path="/" element={<ChatPage />} />
					<Route path="/c/:conversationId" element={<ChatPage />} />
				</Routes>
			</ChatProvider>
		</ErrorBoundary>
	);
}
