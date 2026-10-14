import { useEffect, useRef } from "react";
import Icon from "./Icon";
import MarkdownContent from "./MarkdownContent";

/** A rolling, tail-pinned preview of the active node's streamed text. */
export default function TokenPreview({ text, node }: { text: string; node: string | null }) {
    const ref = useRef<HTMLDivElement>(null);

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
            <div className="stream-window" ref={ref}>
                {text ? (
                    <div className="stream-markdown">
                        <MarkdownContent content={text} compact />
                        <span className="live-caret" />
                    </div>
                ) : (
                    <div className="stream-placeholder"><Icon name="loader" size={16} className="spin" /> Waiting for the first tokens…</div>
                )}
            </div>
            <div className="stream-footer"><span>Tail preview · formatted as it arrives</span><span>{text.length.toLocaleString()} characters</span></div>
        </section>
    );
}
