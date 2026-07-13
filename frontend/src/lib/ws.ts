// Realtime events from the backend — subscribe, don't poll.
//   const live = connect();                          // $live.status / $live.last in a component
//   const live = connect("/ws", (e) => { ... });     // or handle each event as it arrives
// The backend side is app/events.py notify(kind, **data); the gateway is app/ws.py.
import { browser } from "$app/environment";
import { readable, type Readable } from "svelte/store";

export type WsEvent = Record<string, unknown> & { kind?: string };
export type WsState = { status: "connecting" | "open" | "closed"; last: WsEvent | null };

export function connect(path = "/ws", onEvent?: (e: WsEvent) => void): Readable<WsState> {
  return readable<WsState>({ status: "connecting", last: null }, (set) => {
    if (!browser) {
      // SSR/prerender: no socket to open (Node ships a global WebSocket but no page `location`,
      // so feature-sniffing is NOT enough); the browser hydration subscribes again for real.
      set({ status: "closed", last: null });
      return;
    }
    let ws: WebSocket | null = null;
    let last: WsEvent | null = null;
    let tries = 0;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const open = () => {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${proto}://${location.host}${path}`);
      set({ status: "connecting", last });
      ws.onopen = () => {
        tries = 0;
        set({ status: "open", last });
      };
      ws.onmessage = (m) => {
        last = JSON.parse(m.data) as WsEvent;
        set({ status: "open", last });
        onEvent?.(last);
      };
      ws.onclose = () => {
        if (stopped) return;
        set({ status: "closed", last });
        timer = setTimeout(open, Math.min(500 * 2 ** tries++, 15_000)); // capped backoff
      };
    };
    open();
    return () => {
      stopped = true;
      clearTimeout(timer);
      ws?.close();
    };
  });
}
