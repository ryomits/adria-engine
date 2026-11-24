import Foundation

/// The only files under ADRIA_HOME that the web page may read.
/// Keep in sync with HOME_ALLOWLIST in app/web/vite.config.ts.
public enum HomeFiles {
    nonisolated(unsafe) private static let allowlist: [Regex<Substring>] = [
        /display\.json/,
        /avatars\/[^\/]+\.vrm/,
        /runtime\/(?:now_playing|state)/,
    ]

    /// File URL for a page-relative path, or nil if the path is not allowed.
    public static func resolve(_ relativePath: String, home: URL) -> URL? {
        let parts = relativePath.split(separator: "/", omittingEmptySubsequences: false)
        guard !parts.contains(where: { $0 == ".." || $0 == "." || $0.isEmpty }) else { return nil }
        guard allowlist.contains(where: { relativePath.wholeMatch(of: $0) != nil }) else { return nil }
        return home.appendingPathComponent(relativePath)
    }
}
