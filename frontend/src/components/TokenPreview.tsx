import { useEffect, useRef } from "react";
import Icon from "./Icon";

/** A rolling, tail-pinned preview of the active node's streamed text. */
export default function TokenPreview({ text, node }: { text: string; node: string | null }) {
    const ref = useRef<HTMLPreElement>(null);

    useEffect(() => {
        ref.current?.scrollTo({ top: ref.current.scrollHeight });
    }, [text]);

    if (!text && !node) return null;

    return (
        <section className="stream-panel panel" aria-label="Live node output">
            <div className="stream-heading">
                <div className="stream-title"><span className="stream-live-dot" /><span>Live node output</span></div>
                <span className="stream-node"><Icon name="terminal" size={14} /> {node ?? "initializing"}</span>
            </div>
            <div className="stream-window">
                {text ? (
                    <pre ref={ref}>{text}<span className="live-caret" /></pre>
                ) : (
                    <div className="stream-placeholder"><Icon name="loader" size={16} className="spin" /> Waiting for the first tokens…</div>
                )}
            </div>
            <div className="stream-footer"><span>Tail preview · updates as the model responds</span><span>{text.length.toLocaleString()} characters</span></div>
        </section>
    );
}
