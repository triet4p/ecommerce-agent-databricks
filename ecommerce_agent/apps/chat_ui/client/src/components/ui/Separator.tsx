// =============================================================================
// Accessible Separator component (S4-B7)
// =============================================================================

import * as SeparatorPrimitive from "@radix-ui/react-separator";
import React from "react";

const Separator = React.forwardRef<
	React.ComponentRef<typeof SeparatorPrimitive.Root>,
	React.ComponentPropsWithoutRef<typeof SeparatorPrimitive.Root>
>(({ className, orientation = "horizontal", ...props }, ref) => (
	<SeparatorPrimitive.Root
		ref={ref}
		orientation={orientation}
		className={
			orientation === "horizontal"
				? "h-px w-full bg-border"
				: "h-full w-px bg-border"
		}
		{...props}
	/>
));
Separator.displayName = "Separator";

export { Separator };
