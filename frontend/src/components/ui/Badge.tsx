import * as React from "react"
import { cn } from "../../lib/utils"

const Badge = React.forwardRef<
    HTMLDivElement,
    React.HTMLAttributes<HTMLDivElement> & { variant?: "default" | "critical" | "high" | "info" }
>(({ className, variant = "default", ...props }, ref) => {
    const variants = {
        default: "bg-slate-500/10 text-slate-400 border-slate-500/20",
        critical: "bg-red-500/10 text-red-400 border-red-500/20",
        high: "bg-amber-500/10 text-amber-400 border-amber-500/20",
        info: "bg-blue-500/10 text-blue-400 border-blue-500/20"
    }

    return (
        <div
            ref={ref}
            className={cn(
                "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                variants[variant],
                className
            )}
            {...props}
        />
    )
})
Badge.displayName = "Badge"

export { Badge }
