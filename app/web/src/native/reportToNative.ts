// Forwards page events to the native app's log (no-op in a normal browser).
type MessageHandler = { postMessage: (message: string) => void };

function nativeLogHandler(): MessageHandler | undefined {
  const w: unknown = window;
  if (typeof w !== "object" || w === null || !("webkit" in w)) return undefined;
  const webkit: unknown = w.webkit;
  if (typeof webkit !== "object" || webkit === null || !("messageHandlers" in webkit)) return undefined;
  const handlers: unknown = webkit.messageHandlers;
  if (typeof handlers !== "object" || handlers === null || !("log" in handlers)) return undefined;
  const log: unknown = handlers.log;
  if (typeof log !== "object" || log === null || !("postMessage" in log)) return undefined;
  const post: unknown = log.postMessage;
  return typeof post === "function" ? { postMessage: (m) => post.call(log, m) } : undefined;
}

export function reportToNative(message: string): void {
  nativeLogHandler()?.postMessage(message);
}
