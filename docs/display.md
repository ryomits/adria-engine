# Display app

A small window at the edge of the screen (bottom right by default) that shows the character and starts and ends conversations. It is a borderless, transparent AppKit window that hosts a `WKWebView`; the page draws the character and follows the harness through its signal files.

```
harness ──writes──▶ ADRIA_HOME/runtime/state, now_playing ──polled every 50 ms──▶ page
harness ◀──reads─── ADRIA_HOME/runtime/control.jsonl ◀──appends── ADRIA.app (click, quit)
```

- `app/web/`: the page (Vite + TypeScript). It is built into the app, so no CDN is used at runtime.
- `app/mac/`: the native shell (SwiftPM; no Xcode project). `ADRIACore` holds the testable parts.
- The scheme handler serves the bundled page plus **only** these files from ADRIA_HOME: `display.json`, `avatars/*.vrm`, `runtime/now_playing`, `runtime/state`. The dev server enforces the same list.

## Using it

| Action | Result |
|---|---|
| Click the character | Start a conversation (the microphone opens) / end it (back to standby) |
| No speech for `[conversation] idle_timeout_min` minutes | Back to standby by itself |
| Drag | Move the window (not saved; the next start uses `display.json` again) |
| Right-click → Quit ADRIA, or Cmd-Q | Quit the app; the harness saves the conversation summary and exits too |

A click while ADRIA is thinking or speaking lets the current reply finish, then goes to standby.

## The four states

The harness writes the state; the page shows it in two ways: the avatar, and a badge in the top-right corner (color and icon) that stays the same whatever avatar is used.

| State | Meaning | Badge | Placeholder character |
|---|---|---|---|
| `idle` | Standby; microphone closed | grey, "z z" | grey-blue, sleepy eyes, slow bobbing |
| `listening` | Conversation on; microphone open | green, microphone | green, eyes open, a slowly breathing ring |
| `thinking` | Reply being generated or synthesized | amber, three dots | amber, eyes up and aside, dots above the head |
| `speaking` | Reply being played | coral, speaker | coral, the mouth follows the voice |

Motion is deliberately small and slow.

## Avatars (the replaceable layer)

The shell (`app/web/src/main.ts`) turns the signals into one frame per animation frame (`state`, `expression`, `mouth`) and hands it to an `AvatarView` (`app/web/src/avatar/AvatarView.ts`). The shell knows nothing about how the character is drawn:

- `avatar/placeholder/`: a simple round character on a 2D canvas.
- `avatar/vrmAvatar/`: a VRM model with three.js and @pixiv/three-vrm (expressions, lip sync, blinking, procedural motion, per-state framing).

A new avatar is another `AvatarView` implementation plus one line in `createAvatar` in `main.ts`; the window, the badge, the signals and the harness do not change.

## Settings: `ADRIA_HOME/display.json`

```jsonc
{
  "avatar": "placeholder",              // placeholder | vrm (default: vrm when "vrm" is set)
  "vrm": "avatars/your-model.vrm",      // for the vrm avatar; a file directly under ADRIA_HOME/avatars/
  "window": {
    "width": 240, "height": 320,        // default 240 x 320
    "corner": "bottomRight",            // topLeft | topRight | bottomLeft | bottomRight
    "margin": 24,
    "level": "front"                    // front: always on top | normal | back: behind other windows
  },
  "expressions": {                      // vrm: x_expression name -> VRM expression weights
    "neutral": {},
    "happy": { "happy": 1.0 }
  },
  "lipSync": { "expression": "aa", "fallbackHz": 4 },
  "framing": {                          // vrm, optional; per state, any field may be omitted
    "speaking": { "target": [0, 1.25, 0], "distance": 1.6, "fov": 30, "modelX": 0 }
  },
  "transitionSec": 0.8                  // vrm: camera and placement transition time
}
```

The silence timeout is in `config.toml` (`[conversation] idle_timeout_min`), because the harness enforces it.

Swapping VRM models needs no code change: put the VRM under `avatars/`, change `vrm`, and adjust `expressions` and `framing` to the model. Default framing (metres; the camera looks at `target` from `distance` in front; `modelX` shifts the character), made for a model about 1.6 m tall:

| State | target | distance | modelX | Gesture |
|---|---|---|---|---|
| idle | (0, 0.85, 0) | 3.2 | 0.25 | full body; occasional glances |
| listening | (0, 1.1, 0) | 2.2 | 0.1 | small nods |
| thinking | (0, 1.1, 0) | 2.2 | 0.1 | head tilt |
| speaking | (0, 1.25, 0) | 1.6 | 0 | bust-up; slight head motion |

For a shorter model or a narrow window, lower `target` and `modelX` (check with the `still` URL parameters below).

## Commands to the harness: `runtime/control.jsonl`

The app appends one JSON line per command; only the app writes this file.

```json
{"seq": 1, "command": "toggle", "at": 1795787552.4}
{"seq": 2, "command": "quit", "at": 1795787560.1}
```

The harness reads only lines written after it started, so a click while it was down does nothing later. Without the app, `adria voice --start` starts a conversation right away.

## Development

```bash
cd app/web && npx vite          # http://127.0.0.1:5179/ reads ../../../adria-home (or ADRIA_HOME)
npm test                        # vitest
cd ../mac && swift test         # ADRIACore tests
```

URL parameters: `debug` (state, expression and mouth overlay), `checker` (checkerboard background), `avatar=placeholder` (the placeholder whatever display.json says), `vrm=avatars/x.vrm` (another model than display.json), `still&state=…&expr=…&mouth=…` (deterministic frame for offline checks).

A browser tab in the background stops animation frames, so the page stops updating there; the app window is always visible.

The page reports load events and errors to the unified log:

```bash
/usr/bin/log show --last 5m --predicate 'subsystem == "local.adria.display"'
```

(In zsh, `log` is a shell builtin; use `/usr/bin/log`.) The web inspector is available from Safari's Develop menu.

## Checks on the Mac (by a person)

GUI windows and the microphone cannot be verified from a shell session, so these are done on the Mac. Build first with `scripts/build-app.sh`.

Starting

- [ ] Double-click `app/build/ADRIA.app`: the character appears and no Terminal window opens; the first time, macOS asks for microphone permission for ADRIA
- [ ] Quit, then double-click `scripts/start.command`: a Terminal window shows the logs, and only one voice loop runs (no "already running" in the Terminal)
- [ ] After quitting an everyday start, `runtime/logs/harness.log` has no conversation text

Window

- [ ] The character appears in the configured corner, small, with no frame and a transparent background
- [ ] Switching to another app: the character stays visible and in front
- [ ] Moving to another Space (Mission Control): the character is there too
- [ ] Dragging moves the window smoothly; releasing after a drag does not start a conversation
- [ ] Right-click shows "Quit ADRIA"; it quits the app, and the voice loop saves the summary and exits (debug start: visible in the Terminal; everyday start: no `adria` process left after a few seconds)
- [ ] Cmd-Q (with the app in front) does the same
- [ ] Changing `corner`, `width` / `height` in display.json: the window follows after a restart

States and conversation

- [ ] At start: standby (grey badge), and no microphone indicator in the menu bar
- [ ] Click: green badge (listening) and the orange microphone indicator appears
- [ ] Speak: amber (thinking) after you stop, then coral (speaking) while the reply plays; the mouth follows the voice; back to green afterwards
- [ ] Click while green: back to standby; the microphone indicator disappears
- [ ] Click while speaking: the reply finishes, then standby
- [ ] Stay silent for the timeout (set `idle_timeout_min = 1` to check quickly): back to standby by itself, and a summary appears in `memory/summary.md` if something worth remembering was said
- [ ] The four states are easy to tell apart at a glance from a child's distance, and the motion is calm
- [ ] With `"avatar": "vrm"`: the same badge and states, and the framing moves between states without jumps
