import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, test, vi } from "vitest";
import Sidebar from "../../client/src/components/Sidebar";

function LocationProbe() {
	return <span data-testid="location">{useLocation().pathname}</span>;
}

describe("Sidebar", () => {
	test("navigates to a selected conversation and creates a new one", () => {
		const onCreate = vi.fn();
		render(
			<MemoryRouter initialEntries={["/"]}>
				<Routes>
					<Route
						path="*"
						element={
							<>
								<Sidebar
									conversations={[
										{
											id: "conversation-1",
											title: "Order help",
											created_at: new Date(0).toISOString(),
											updated_at: new Date(0).toISOString(),
										},
									]}
									isLoading={false}
									onCreate={onCreate}
									onRename={vi.fn()}
									onDelete={vi.fn()}
									isOpen={true}
								/>
								<LocationProbe />
							</>
						}
					/>
				</Routes>
			</MemoryRouter>,
		);

		fireEvent.click(screen.getByRole("button", { name: "New conversation" }));
		expect(onCreate).toHaveBeenCalledOnce();
		fireEvent.click(screen.getByRole("button", { name: /^Order help$/ }));
		expect(screen.getByTestId("location")).toHaveTextContent(
			"/c/conversation-1",
		);
	});

	test("shows loading and empty states", () => {
		const { rerender } = render(
			<MemoryRouter>
				<Sidebar
					conversations={[]}
					isLoading={true}
					onCreate={vi.fn()}
					onRename={vi.fn()}
					onDelete={vi.fn()}
					isOpen={true}
				/>
			</MemoryRouter>,
		);
		expect(screen.getByLabelText("Loading conversations")).toBeVisible();

		rerender(
			<MemoryRouter>
				<Sidebar
					conversations={[]}
					isLoading={false}
					onCreate={vi.fn()}
					onRename={vi.fn()}
					onDelete={vi.fn()}
					isOpen={true}
				/>
			</MemoryRouter>,
		);
		expect(screen.getByText("No conversations yet.")).toBeVisible();
	});
});
