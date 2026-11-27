import { parseNowPlaying, parseState, type ConversationState, type NowPlaying } from "./parseSignals";

type Signals = { state: ConversationState; nowPlaying: NowPlaying | null };

async function fetchJson(url: string): Promise<unknown> {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return res.json();
}

/** Poll the harness signal files and report every result (also on errors). */
export function pollSignals(onSignals: (s: Signals) => void, intervalMs = 50): void {
  const tick = async () => {
    try {
      const [state, np] = await Promise.all([
        fetchJson("home/runtime/state"),
        fetchJson("home/runtime/now_playing"),
      ]);
      onSignals({ state: parseState(state), nowPlaying: parseNowPlaying(np) });
    } catch (err) {
      // Harness not running: show the idle character.
      console.debug("signals unavailable:", err);
      onSignals({ state: "idle", nowPlaying: null });
    }
    setTimeout(tick, intervalMs);
  };
  void tick();
}
