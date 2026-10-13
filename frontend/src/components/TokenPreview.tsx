import { useEffect, useRef } from "react";

/** A rolling preview of the active node's streamed text. */
export default function TokenPreview({ text, node }: { text: string; node: string | null }) {
    const ref = useRef<HTMLPreElement>(null);

    useEffect(() => {
        ref.current?.scrollTo({ top: ref.current.scrollHeight });
    }, [text]);

    if (!text) return null;
    return (
        <div className="rounded border border-line bg-panel p-3">
            <div className="text-xs uppercase tracking-wide text-slate-500 mb-2">
                {node ?? "streaming"}
            </div>
            <pre
                ref={ref}
                className="max-h-48 overflow-y-auto scrollbar-thin whitespace-pre-wrap break-words text-xs text-slate-300"
            >
                {text}
            </pre>
        </div>
    );
}