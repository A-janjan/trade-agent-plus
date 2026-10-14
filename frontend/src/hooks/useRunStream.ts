import { useEffect, useRef, useState } from "react";
import type { StreamEvent } from "../types";

interface StreamState {
    runId: string | null;
    events: StreamEvent[];
    connected: boolean;
    done: boolean;
    streamError: string | null;
}

const EMPTY_STATE: StreamState = {
    runId: null,
    events: [],
    connected: false,
    done: false,
    streamError: null,
};

function eventSignature(event: StreamEvent) {
    // The API replays the event history when an EventSource reconnects. There
    // are no wire-level event IDs yet, so the serialized payload is the stable
    // identity used to prevent a reconnect from duplicating the transcript.
    return JSON.stringify(event);
}

/** Subscribe to a run's SSE stream and rebuild its view from normalized events. */
export function useRunStream(runId: string | null) {
    const [state, setState] = useState<StreamState>(EMPTY_STATE);
    const seenRef = useRef<Set<string>>(new Set());

    useEffect(() => {
        if (!runId) return;

        seenRef.current = new Set();
        const source = new EventSource(`/api/runs/${runId}/stream`);
        let terminal = false;

        source.onopen = () => {
            setState((current) => ({
                ...(current.runId === runId ? current : { ...EMPTY_STATE, runId }),
                connected: true,
                streamError: null,
            }));
        };

        source.onerror = () => {
            if (terminal) return;
            setState((current) => ({
                ...(current.runId === runId ? current : { ...EMPTY_STATE, runId }),
                connected: false,
                streamError: "The live stream is reconnecting…",
            }));
        };

        source.onmessage = (message) => {
            try {
                const event = JSON.parse(message.data) as StreamEvent;
                const signature = eventSignature(event);
                if (seenRef.current.has(signature)) return;
                seenRef.current.add(signature);

                const isTerminal = event.type === "run.finished" || event.type === "run.failed";
                if (isTerminal) {
                    terminal = true;
                    source.close();
                }

                setState((current) => {
                    const base = current.runId === runId ? current : { ...EMPTY_STATE, runId };
                    return {
                        ...base,
                        events: [...base.events, event],
                        connected: isTerminal ? false : base.connected,
                        done: isTerminal || base.done,
                        streamError: null,
                    };
                });
            } catch {
                setState((current) => ({
                    ...(current.runId === runId ? current : { ...EMPTY_STATE, runId }),
                    streamError: "A malformed event was ignored; the stream will continue.",
                }));
            }
        };

        return () => {
            terminal = true;
            source.close();
        };
    }, [runId]);

    // A route change should show a clean loading state immediately, before the
    // new EventSource has produced its first frame.
    const visible = state.runId === runId ? state : EMPTY_STATE;
    return {
        events: visible.events,
        connected: visible.connected,
        done: visible.done,
        streamError: visible.streamError,
    };
}
