import type { SVGProps } from "react";

export type IconName =
    | "activity"
    | "alert"
    | "arrowDown"
    | "arrowRight"
    | "arrowUpRight"
    | "calendar"
    | "check"
    | "chevronDown"
    | "chevronRight"
    | "clock"
    | "database"
    | "eye"
    | "fileText"
    | "globe"
    | "history"
    | "layers"
    | "link"
    | "loader"
    | "play"
    | "plus"
    | "pulse"
    | "refresh"
    | "search"
    | "shield"
    | "spark"
    | "sparkles"
    | "terminal"
    | "trend"
    | "x"
    | "zap";

type Props = Omit<SVGProps<SVGSVGElement>, "name"> & {
    name: IconName;
    size?: number;
};

/** A tiny dependency-free icon set for the workspace UI. */
export default function Icon({ name, size = 18, strokeWidth = 1.8, ...props }: Props) {
    const common = {
        width: size,
        height: size,
        viewBox: "0 0 24 24",
        fill: "none",
        stroke: "currentColor",
        strokeWidth,
        strokeLinecap: "round" as const,
        strokeLinejoin: "round" as const,
        "aria-hidden": true,
        focusable: false,
        ...props,
    };

    switch (name) {
        case "activity":
            return <svg {...common}><path d="M3 12h4l2.2-7 4.1 14 2.5-7H21" /></svg>;
        case "alert":
            return <svg {...common}><path d="m12 3 9 16H3L12 3Z" /><path d="M12 9v4M12 16h.01" /></svg>;
        case "arrowDown":
            return <svg {...common}><path d="M12 4v15M6 13l6 6 6-6" /></svg>;
        case "arrowRight":
            return <svg {...common}><path d="M4 12h15M13 6l6 6-6 6" /></svg>;
        case "arrowUpRight":
            return <svg {...common}><path d="M5 19 19 5M9 5h10v10" /></svg>;
        case "calendar":
            return <svg {...common}><rect x="3" y="4.5" width="18" height="16" rx="2" /><path d="M16 2.5v4M8 2.5v4M3 9h18" /></svg>;
        case "check":
            return <svg {...common}><path d="m5 12 4.3 4.3L19 6.7" /></svg>;
        case "chevronDown":
            return <svg {...common}><path d="m6 9 6 6 6-6" /></svg>;
        case "chevronRight":
            return <svg {...common}><path d="m9 6 6 6-6 6" /></svg>;
        case "clock":
            return <svg {...common}><circle cx="12" cy="12" r="8.5" /><path d="M12 7v5l3.5 2" /></svg>;
        case "database":
            return <svg {...common}><ellipse cx="12" cy="5" rx="7.5" ry="3" /><path d="M4.5 5v7c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3V5M4.5 12v7c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3v-7" /></svg>;
        case "eye":
            return <svg {...common}><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" /><circle cx="12" cy="12" r="2.5" /></svg>;
        case "fileText":
            return <svg {...common}><path d="M6 3.5h8l4 4v13H6z" /><path d="M14 3.5v4h4M9 12h6M9 16h6" /></svg>;
        case "globe":
            return <svg {...common}><circle cx="12" cy="12" r="8.5" /><path d="M3.8 9h16.4M3.8 15h16.4M12 3.5c2.2 2.3 3.2 5.1 3.2 8.5s-1 6.2-3.2 8.5c-2.2-2.3-3.2-5.1-3.2-8.5S9.8 5.8 12 3.5Z" /></svg>;
        case "history":
            return <svg {...common}><path d="M3.5 12a8.5 8.5 0 1 0 2.5-6" /><path d="M3.5 4.5V9h4.5M12 7v5l3.2 1.8" /></svg>;
        case "layers":
            return <svg {...common}><path d="m12 3 8.5 4.5L12 12 3.5 7.5 12 3Z" /><path d="m3.5 12 8.5 4.5 8.5-4.5M3.5 16.5 12 21l8.5-4.5" /></svg>;
        case "link":
            return <svg {...common}><path d="m9.5 14.5 5-5M7.2 17.8l-1.1 1.1a3.5 3.5 0 0 1-5-5l3-3a3.5 3.5 0 0 1 5 0M16.8 6.2l1.1-1.1a3.5 3.5 0 0 1 5 5l-3 3a3.5 3.5 0 0 1-5 0" /></svg>;
        case "loader":
            return <svg {...common}><path d="M12 3a9 9 0 1 0 9 9" /></svg>;
        case "play":
            return <svg {...common}><path d="m9 5 10 7-10 7V5Z" /></svg>;
        case "plus":
            return <svg {...common}><path d="M12 5v14M5 12h14" /></svg>;
        case "pulse":
            return <svg {...common}><path d="M3 12h3l2-5 4 10 2.2-6H21" /><path d="M3 4v16" opacity=".35" /></svg>;
        case "refresh":
            return <svg {...common}><path d="M20 11a8 8 0 0 0-14-4L4 9" /><path d="M4 4v5h5M4 13a8 8 0 0 0 14 4l2-2" /><path d="M20 20v-5h-5" /></svg>;
        case "search":
            return <svg {...common}><circle cx="10.8" cy="10.8" r="6.5" /><path d="m16 16 5 5" /></svg>;
        case "shield":
            return <svg {...common}><path d="M12 3 19 6v5.5c0 4.5-3 7.8-7 9.5-4-1.7-7-5-7-9.5V6l7-3Z" /><path d="m8.5 12 2.3 2.3 4.7-5" /></svg>;
        case "spark":
            return <svg {...common}><path d="m12 2 1.6 6.4L20 10l-6.4 1.6L12 18l-1.6-6.4L4 10l6.4-1.6L12 2Z" /><path d="m19 16 .7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7L19 16Z" /></svg>;
        case "sparkles":
            return <svg {...common}><path d="m12 2 1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2Z" /><path d="m19 16 .6 2.4L22 19l-2.4.6L19 22l-.6-2.4L16 19l2.4-.6L19 16Z" /></svg>;
        case "terminal":
            return <svg {...common}><rect x="3" y="4" width="18" height="16" rx="2" /><path d="m7 9 3 3-3 3M13 15h4" /></svg>;
        case "trend":
            return <svg {...common}><path d="M4 17 9 12l3.5 3.5L20 8" /><path d="M15 8h5v5" /></svg>;
        case "x":
            return <svg {...common}><path d="m6 6 12 12M18 6 6 18" /></svg>;
        case "zap":
            return <svg {...common}><path d="m13 2-8 12h6l-1 8 8-12h-6l1-8Z" /></svg>;
    }
}
