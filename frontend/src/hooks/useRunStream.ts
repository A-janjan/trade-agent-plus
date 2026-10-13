import { useEffect, useRef, useState } from "react";
import type { StreamEvent } from "../types";

/**
 * Subscribes to a run's SSE stream and accumulates events.
 *
 * Reconnection is automatic: EventSource retries on transport errors by
 * default. The server replays the event history on every (re)connect, so the
 * client can accumulate without deduplicating — no event arrives twice on a
 * single connection, and a reconnect restarts the accumulation from scratch.
 */
export function useRunStream(runId: string | null) {
    const [events, setEvents] = useState<StreamEvent[]>([]);
    const [connected, setConnected] = useState(false);
    const [done, setDone] = useState(false);
    const sourceRef = useRef<EventSource | null>(null);

    useEffect(() => {
        if (!runId) return;
        setEvents([]);
        setDone(false);

        const source = new EventSource(`/api/runs/${runId}/stream`);
        sourceRef.current = source;

        source.onopen = () => setConnected(true);
        source.onerror = () => setConnected(false);
        source.onmessage = (msg) => {
            try {
                const event = JSON.parse(msg.data) as StreamEvent;
                setEvents((prev) => [...prev, event]);
                if (event.type === "run.finished" || event.type === "run.failed") {
                    setDone(true);
                    source.close();
                }
            } catch {
                // Ignore malformed frames; the stream is trusted but a bad frame
                // should not kill the connection.
            }
        };

        return () => {
            source.close();
            sourceRef.current = null;
        };
    }, [runId]);

    return { events, connected, done };
}