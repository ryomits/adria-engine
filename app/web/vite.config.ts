import fs from "node:fs";
import path from "node:path";
import { defineConfig, type Plugin } from "vite";

// Files under ADRIA_HOME that the page may read. The native app's URL scheme
// handler enforces the same list (see app/mac/Sources/ADRIA/HomeFiles.swift).
const HOME_ALLOWLIST = [
  /^display\.json$/,
  /^avatars\/[^/]+\.vrm$/,
  /^runtime\/(now_playing|state)$/,
];

/** Dev-only: serve allowlisted files from ADRIA_HOME at /home/... */
function serveHome(): Plugin {
  return {
    name: "adria-serve-home",
    configureServer(server) {
      const home = process.env.ADRIA_HOME
        ? path.resolve(process.env.ADRIA_HOME)
        : path.resolve(__dirname, "../../../adria-home");
      server.middlewares.use("/home/", (req, res, next) => {
        const rel = decodeURIComponent((req.url ?? "").split("?")[0].replace(/^\//, ""));
        if (!HOME_ALLOWLIST.some((re) => re.test(rel))) {
          res.statusCode = 404;
          res.end();
          return;
        }
        const file = path.join(home, rel);
        fs.readFile(file, (err, data) => {
          if (err) return next();
          res.setHeader("Cache-Control", "no-store");
          res.end(data);
        });
      });
    },
  };
}

export default defineConfig({
  base: "./",
  plugins: [serveHome()],
  server: { host: "127.0.0.1", port: 5179, strictPort: true },
  build: { outDir: "dist", emptyOutDir: true, chunkSizeWarningLimit: 2000 },
});
