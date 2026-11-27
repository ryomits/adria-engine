import ADRIACore
import AppKit
import WebKit

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    private var window: CharacterWindow?
    private var control: ControlChannel?

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
        let bundled = Bundle.main.url(forResource: "adria_home", withExtension: nil)
            .flatMap { try? String(contentsOf: $0, encoding: .utf8) }
        return HomeLocator.locate(environment: ProcessInfo.processInfo.environment, bundledPath: bundled)
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
