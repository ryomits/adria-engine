import Foundation

/// Sends commands to the harness by appending JSON lines to ADRIA_HOME/runtime/control.jsonl.
/// The harness reads only lines written after it started.
public final class ControlChannel: @unchecked Sendable {
    public enum Command: String, Sendable {
        /// Start a conversation, or end the running one (a click on the character).
        case toggle
        /// The app is quitting: the harness ends the session and exits.
        case quit
    }

    private let file: URL
    private let lock = NSLock()
    private var seq = 0

    public init(runtime: URL) {
        file = runtime.appendingPathComponent("control.jsonl")
    }

    public func send(_ command: Command) throws {
        lock.lock()
        defer { lock.unlock() }
        seq += 1
        let line = try JSONSerialization.data(withJSONObject: [
            "seq": seq, "command": command.rawValue, "at": Date().timeIntervalSince1970,
        ]) + Data("\n".utf8)
        try FileManager.default.createDirectory(at: file.deletingLastPathComponent(),
                                                withIntermediateDirectories: true)
        if !FileManager.default.fileExists(atPath: file.path) {
            FileManager.default.createFile(atPath: file.path, contents: nil,
                                           attributes: [.posixPermissions: 0o600])
        }
        let handle = try FileHandle(forWritingTo: file)
        defer { try? handle.close() }
        try handle.seekToEnd()
        // One write call per line, so the harness never sees half a command
        // followed by another one.
        try handle.write(contentsOf: line)
    }
}
