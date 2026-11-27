import Foundation
import Testing
@testable import ADRIACore

struct ControlChannelTests {
    func tempRuntime() throws -> URL {
        let dir = FileManager.default.temporaryDirectory
            .appendingPathComponent("adria-control-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }

    func lines(_ runtime: URL) throws -> [[String: Any]] {
        let text = try String(contentsOf: runtime.appendingPathComponent("control.jsonl"), encoding: .utf8)
        return try text.split(separator: "\n").map {
            try JSONSerialization.jsonObject(with: Data($0.utf8)) as! [String: Any]
        }
    }

    @Test func writesTheCommandAsOneJSONLine() throws {
        let runtime = try tempRuntime()
        try ControlChannel(runtime: runtime).send(.toggle)
        #expect(try lines(runtime).first?["command"] as? String == "toggle")
    }

    @Test func appendsLaterCommands() throws {
        let runtime = try tempRuntime()
        let channel = ControlChannel(runtime: runtime)
        try channel.send(.toggle)
        try channel.send(.quit)
        #expect(try lines(runtime).map { $0["command"] as? String } == ["toggle", "quit"])
    }

    @Test func numbersTheCommands() throws {
        let runtime = try tempRuntime()
        let channel = ControlChannel(runtime: runtime)
        try channel.send(.toggle)
        try channel.send(.toggle)
        #expect(try lines(runtime).map { $0["seq"] as? Int } == [1, 2])
    }

    @Test func createsTheRuntimeDirectory() throws {
        let runtime = try tempRuntime().appendingPathComponent("runtime")
        try ControlChannel(runtime: runtime).send(.toggle)
        #expect(try lines(runtime).count == 1)
    }
}
