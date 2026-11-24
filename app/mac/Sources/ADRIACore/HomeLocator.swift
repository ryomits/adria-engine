import Foundation

/// Finds the private ADRIA_HOME directory.
///
/// A double-clicked app gets no shell environment, so the build script records
/// the path in the bundle; ADRIA_HOME in the environment still takes priority.
public enum HomeLocator {
    public static func locate(environment: [String: String], bundledPath: String?) -> URL? {
        if let env = environment["ADRIA_HOME"], !env.isEmpty {
            return URL(fileURLWithPath: env)
        }
        let bundled = bundledPath?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return bundled.isEmpty ? nil : URL(fileURLWithPath: bundled)
    }
}
