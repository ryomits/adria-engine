// Small badge in the corner of the window that shows the conversation state
// with a color and an icon. It belongs to the app, not to the avatar, so it
// stays the same when the avatar is replaced.
import type { ConversationState } from "../signals/parseSignals";

type Badge = { color: string; icon: string; label: string };

// Icons are inline SVG paths in a 24x24 box.
const BADGES: Record<ConversationState, Badge> = {
  idle: {
    color: "#8E9AAB",
    // "z z": asleep / standby
    icon: "M5 7h6l-6 7h6M13 4h5l-5 6h5",
    label: "おやすみ中（クリックでおはなし）",
  },
  listening: {
    color: "#3FAE7A",
    // microphone
    icon: "M12 3a3 3 0 0 0-3 3v5a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3zM6 11a6 6 0 0 0 12 0M12 17v4",
    label: "きいているよ",
  },
  thinking: {
    color: "#E0A030",
    // three dots
    icon: "M6 12h.01M12 12h.01M18 12h.01",
    label: "かんがえ中",
  },
  speaking: {
    color: "#E2725B",
    // speaker with waves
    icon: "M4 10v4h4l5 4V6L8 10zM16 9a4 4 0 0 1 0 6M18.5 6.5a7.5 7.5 0 0 1 0 11",
    label: "おはなし中",
  },
};

export function badgeFor(state: ConversationState): Badge {
  return BADGES[state];
}

/** Create the badge element; returns a function that shows a state. */
export function mountStateBadge(parent: HTMLElement): (state: ConversationState) => void {
  const el = document.createElement("div");
  el.id = "state-badge";
  el.setAttribute("role", "status");
  const svgNs = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNs, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  const path = document.createElementNS(svgNs, "path");
  svg.appendChild(path);
  el.appendChild(svg);
  parent.appendChild(el);
  let shown: ConversationState | null = null;
  return (state) => {
    if (state === shown) return;
    shown = state;
    const b = badgeFor(state);
    el.style.backgroundColor = b.color;
    el.dataset.state = state;
    el.setAttribute("aria-label", b.label);
    path.setAttribute("d", b.icon);
  };
}
