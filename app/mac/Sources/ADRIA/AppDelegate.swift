import ADRIACore
import AppKit
import WebKit

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    private var window: CharacterWindow?
    private var control: ControlChannel?
    private var harness: Process?

    func applicationDidFinishLaunching(_ notification: Notification) {
        installMenu()
        guard let home = locateHome() else {
            fail("ADRIA_HOME is not known. Rebuild the app with scripts/build-app.sh, or set ADRIA_HOME.")
            return
        }
        let settings: WindowSettings
        do {
            settings = try WindowSettings.fromDisplayJSON(Data(contentsOf: home.appendingPathComponent("display.json")))
        } catch {
            fail("Could not read display.json in \(home.path): \(error)")
            return
        }
        guard let webRoot = Bundle.main.resourceURL?.appendingPathComponent("web") else {
            fail("The app bundle has no web resources.")
            return
        }
        let control = ControlChannel(runtime: home.appendingPathComponent("runtime"))
        self.control = control
        let window = CharacterWindow(settings: settings, home: home, webRoot: webRoot) {
            Self.send(.toggle, via: control)
        }
        window.orderFrontRegardless()
        self.window = window
        startHarness(home: home)
    }

    /// Everyday use: the app runs the voice loop itself, so no Terminal window is needed.
    /// The voice loop exits by itself when the app sends "quit".
    private func startHarness(home: URL) {
        guard let plan = HarnessLaunch.plan(
            arguments: CommandLine.arguments, environment: ProcessInfo.processInfo.environment,
            enginePath: Self.bundledString("adria_engine"), searchPath: Self.bundledString("search_path"),
            home: home)
        else {
            pageLogger.notice("voice loop not started by the app (debug start or unknown engine)")
            return
        }
        do {
            try FileManager.default.createDirectory(at: plan.logFile.deletingLastPathComponent(),
                                                    withIntermediateDirectories: true)
            FileManager.default.createFile(atPath: plan.logFile.path, contents: nil)  // a fresh log per start
            let process = Process()
            process.executableURL = plan.executable
            process.arguments = plan.arguments
            process.environment = plan.environment
            process.standardInput = FileHandle.nullDevice
            process.standardOutput = FileHandle.nullDevice  // progress and conversation lines
            process.standardError = try FileHandle(forWritingTo: plan.logFile)
            process.terminationHandler = { p in
                pageLogger.notice("voice loop exited with status \(p.terminationStatus, privacy: .public)")
            }
            try process.run()
            harness = process
            pageLogger.notice("voice loop started (pid \(process.processIdentifier, privacy: .public))")
        } catch {
            fail("Could not start the voice loop: \(error.localizedDescription). See \(plan.logFile.path).")
        }
    }

    private static func bundledString(_ name: String) -> String? {
        Bundle.main.url(forResource: name, withExtension: nil)
            .flatMap { try? String(contentsOf: $0, encoding: .utf8) }?
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    /// Quitting the app (menu, Cmd-Q, Dock) also ends the conversation and the harness.
    func applicationWillTerminate(_ notification: Notification) {
        if let control { Self.send(.quit, via: control) }
    }

    private static func send(_ command: ControlChannel.Command, via control: ControlChannel) {
        do {
            try control.send(command)
        } catch {
            pageLogger.error("could not send \(command.rawValue, privacy: .public): \(error.localizedDescription, privacy: .public)")
        }
    }

    private func locateHome() -> URL? {
        HomeLocator.locate(environment: ProcessInfo.processInfo.environment,
                           bundledPath: Self.bundledString("adria_home"))
    }

    private func installMenu() {
        let main = NSMenu()
        let appItem = NSMenuItem()
        main.addItem(appItem)
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "Quit ADRIA", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        NSApp.mainMenu = main
    }

    private func fail(_ message: String) {
        let alert = NSAlert()
        alert.messageText = "ADRIA cannot start"
        alert.informativeText = message
        alert.runModal()
        NSApp.terminate(nil)
    }
}
