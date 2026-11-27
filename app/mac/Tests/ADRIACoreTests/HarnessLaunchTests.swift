import Foundation
import Testing
@testable import ADRIACore

struct HarnessLaunchTests {
    let home = URL(fileURLWithPath: "/tmp/home")

    func plan(_ arguments: [String] = ["ADRIA"], engine: String? = "/tmp/engine",
              path: String? = "/opt/bin:/usr/bin") -> HarnessLaunch? {
        HarnessLaunch.plan(arguments: arguments, environment: [:], enginePath: engine,
                           searchPath: path, home: home)
    }

    @Test func notStartedWhenTheVoiceLoopRunsElsewhere() {
        #expect(plan(["ADRIA", "--no-harness"]) == nil)
    }

    @Test func notStartedWithoutTheEngineLocation() {
        #expect(plan(engine: nil) == nil)
    }

    @Test func runsTheVoiceLoopQuietlyThroughTheEngineScript() {
        #expect(plan()?.arguments == ["/tmp/engine/scripts/harness.sh", "--quiet", "voice"])
    }

    @Test func runsTheScriptWithBash() {
        #expect(plan()?.executable.path == "/bin/bash")
    }

    @Test func usesTheSearchPathRecordedAtBuildTime() {
        #expect(plan()?.environment["PATH"] == "/opt/bin:/usr/bin")
    }

    @Test func passesTheHomeDirectory() {
        #expect(plan()?.environment["ADRIA_HOME"] == "/tmp/home")
    }

    @Test func logsIntoTheRuntimeDirectory() {
        #expect(plan()?.logFile.path == "/tmp/home/runtime/logs/harness.log")
    }
}
