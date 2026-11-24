# Display app

The character is drawn by a small native app: a borderless, transparent AppKit window that hosts a `WKWebView`. The page uses three.js and @pixiv/three-vrm to render a VRM model and follows the harness through its signal files.

```
harness ──writes──▶ ADRIA_HOME/runtime/state, now_playing
                                  │  polled every 50 ms
ADRIA.app ─ WKWebView ─ page ◀────┘  (adria://app/... scheme handler)
```

- `app/web/`: the page (Vite + TypeScript). It is built into the app, so no CDN is used at runtime.
- `app/mac/`: the native shell (SwiftPM; no Xcode project). `ADRIACore` holds the testable parts.
- The scheme handler serves the bundled page plus **only** these files from ADRIA_HOME: `display.json`, `avatars/*.vrm`, `runtime/now_playing`, `runtime/state`. The dev server enforces the same list.

## Settings: `ADRIA_HOME/display.json`

```jsonc
{
  "vrm": "avatars/your-model.vrm",      // required, under ADRIA_HOME/avatars/
  "window": {
    "width": 420, "height": 640,
    "corner": "bottomRight",            // topLeft | topRight | bottomLeft | bottomRight
    "margin": 24,
    "level": "front",                   // front: always on top | normal | back: behind other windows
    "clickThrough": false               // true: clicks pass through (default off so a child can touch it)
  },
  "expressions": {                      // x_expression name -> VRM expression weights
    "neutral": {},
    "happy": { "happy": 1.0 }
  },
  "lipSync": { "expression": "aa", "fallbackHz": 4 },
  "framing": {                          // optional; per state, any field may be omitted
    "speaking": { "target": [0, 1.25, 0], "distance": 1.6, "fov": 30, "modelX": 0 }
  },
  "transitionSec": 0.8                  // camera and placement transition time
}
```

Swapping models needs no code change: put the VRM under `avatars/`, change `vrm`, and adjust `expressions` and `framing` to the model.

Default framing (metres; the camera looks at `target` from `distance` in front; `modelX` shifts the character):

| State | target | distance | modelX | Gesture |
|---|---|---|---|---|
| idle | (0, 0.85, 0) | 3.2 | 0.25 | full body; occasional glances |
| listening | (0, 1.1, 0) | 2.2 | 0.1 | small nods |
| thinking | (0, 1.1, 0) | 2.2 | 0.1 | head tilt |
| speaking | (0, 1.25, 0) | 1.6 | 0 | bust-up; slight head motion |

Blinking, breathing and spring bones (hair) run on the display side on their own.

## Development

```bash
cd app/web && npx vite          # http://127.0.0.1:5179/ reads ../../../adria-home (or ADRIA_HOME)
npm test                        # vitest
cd ../mac && swift test         # ADRIACore tests
```

URL parameters: `debug` (state, expression and mouth overlay), `checker` (checkerboard background), `vrm=avatars/x.vrm` (another model than display.json), `still&state=…&expr=…&mouth=…` (deterministic frame for offline checks).

The page reports load events and errors to the unified log:

```bash
/usr/bin/log show --last 5m --predicate 'subsystem == "local.adria.display"'
```

(In zsh, `log` is a shell builtin; use `/usr/bin/log`.) The web inspector is available from Safari's Develop menu.

## Checks on the Mac (by a person)

GUI windows cannot be verified from a shell session, so these are done by double-clicking the app.

- [ ] `scripts/build-app.sh`, then double-click `app/build/ADRIA.app`: the character appears in the configured corner with no frame and a transparent background
- [ ] Switch to another app: the character stays visible (with `level: front`)
- [ ] Move to another Space (Mission Control): the character is there too
- [ ] `level: back`: the character stays behind other windows
- [ ] `clickThrough: true`: clicks reach the window behind; `false`: they do not
- [ ] Change `corner`, `width` / `height`: the window follows after a restart
- [ ] Cmd-Q quits the app like a normal app
- [ ] Talk to it (`scripts/start.command`): expression and mouth follow the voice, and the framing moves between idle / listening / thinking / speaking without jumps
