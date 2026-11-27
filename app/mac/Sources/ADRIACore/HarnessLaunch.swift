import Foundation

/// How the app starts the voice loop when it is opened by itself (everyday
/// use, no Terminal window). Started by `scripts/start.sh` (debug), the app
/// gets `--no-harness` because the voice loop already runs in the Terminal.
public struct HarnessLaunch: Equatable, Sendable {
    public let executable: URL
    public let arguments: [String]
    public let environment: [String: String]
    /// Warnings and errors of the voice loop (it is started with --quiet, so no conversation text).
    public let logFile: URL

    /// - Parameters:
    ///   - enginePath: adria-engine checkout, recorded in the bundle at build time.
    ///   - searchPath: PATH at build time; a double-clicked app does not get the shell's PATH,
    ///     and the harness needs uv.
    public static func plan(arguments: [String], environment: [String: String],
                            enginePath: String?, searchPath: String?, home: URL) -> HarnessLaunch? {
        if arguments.contains("--no-harness") { return nil }
        guard let enginePath, !enginePath.isEmpty else { return nil }
        let script = URL(fileURLWithPath: enginePath).appendingPathComponent("scripts/harness.sh")
        var env = environment
        if let searchPath, !searchPath.isEmpty { env["PATH"] = searchPath }
        env["ADRIA_HOME"] = home.path
        return HarnessLaunch(
            executable: URL(fileURLWithPath: "/bin/bash"),
            arguments: [script.path, "--quiet", "voice"],
            environment: env,
            logFile: home.appendingPathComponent("runtime/logs/harness.log")
        )
    }
}
