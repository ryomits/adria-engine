import ADRIACore
import AppKit
import WebKit
import os

let pageLogger = Logger(subsystem: "local.adria.display", category: "page")

/// Small borderless, transparent window at the screen edge that shows only the character.
/// A click starts or ends a conversation, a drag moves the window, and the
/// right-click menu quits the app.
@MainActor
final class CharacterWindow: NSWindow {
    private let schemeHandler: AppSchemeHandler
    private let navigationLog = NavigationLog()

    init(settings: WindowSettings, home: URL, webRoot: URL, onClick: @escaping () -> Void) {
        schemeHandler = AppSchemeHandler(webRoot: webRoot, home: home)
        let screen = NSScreen.main?.visibleFrame ?? CGRect(x: 0, y: 0, width: 1440, height: 900)
        let frame = settings.frame(in: screen)
        super.init(contentRect: frame, styleMask: [.borderless], backing: .buffered, defer: false)
        isOpaque = false
        backgroundColor = .clear
        hasShadow = false
        isReleasedWhenClosed = false
        // Stay visible on every Space and when other apps are in front.
        collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary, .ignoresCycle]
        level = Self.windowLevel(settings.level)

        let config = WKWebViewConfiguration()
        config.setURLSchemeHandler(schemeHandler, forURLScheme: AppSchemeHandler.scheme)
        config.userContentController.add(PageLog(), name: "log")
        let bounds = CGRect(origin: .zero, size: frame.size)
        let webView = WKWebView(frame: bounds, configuration: config)
        webView.setValue(false, forKey: "drawsBackground")  // transparent page background
        webView.underPageBackgroundColor = .clear
        webView.isInspectable = true  // Safari Web Inspector for local debugging
        webView.autoresizingMask = [.width, .height]
        webView.navigationDelegate = navigationLog

        // The page only draws; all mouse input goes to this overlay.
        let input = PointerView(frame: bounds, onClick: onClick)
        input.autoresizingMask = [.width, .height]
        let container = NSView(frame: bounds)
        container.addSubview(webView)
        container.addSubview(input)
        contentView = container
        webView.load(URLRequest(url: URL(string: "\(AppSchemeHandler.scheme)://app/index.html")!))
    }

    override var canBecomeKey: Bool { true }

    private static func windowLevel(_ level: WindowSettings.Level) -> NSWindow.Level {
        switch level {
        case .front: return .floating
        case .normal: return .normal
        case .back: return NSWindow.Level(rawValue: Int(CGWindowLevelForKey(.desktopIconWindow)) + 1)
        }
    }
}

/// Transparent view over the page: click, drag to move, right-click menu.
@MainActor
final class PointerView: NSView {
    private let onClick: () -> Void
    private var gesture: PointerGesture?

    init(frame: CGRect, onClick: @escaping () -> Void) {
        self.onClick = onClick
        super.init(frame: frame)
        menu = Self.contextMenu()
    }

    required init?(coder: NSCoder) { fatalError("not used") }

    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }  // react even when inactive

    override func mouseDown(with event: NSEvent) {
        guard let window else { return }
        gesture = PointerGesture(down: NSEvent.mouseLocation, windowOrigin: window.frame.origin)
    }

    override func mouseDragged(with event: NSEvent) {
        guard let origin = gesture?.moved(to: NSEvent.mouseLocation) else { return }
        window?.setFrameOrigin(origin)
    }

    override func mouseUp(with event: NSEvent) {
        defer { gesture = nil }
        if gesture?.isClick == true { onClick() }
    }

    private static func contextMenu() -> NSMenu {
        let menu = NSMenu()
        menu.addItem(withTitle: "Quit ADRIA", action: #selector(NSApplication.terminate(_:)),
                     keyEquivalent: "")
        return menu
    }
}

/// Writes messages from the page to the unified log (`log show --predicate 'subsystem == "local.adria.display"'`).
final class PageLog: NSObject, WKScriptMessageHandler {
    func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
        pageLogger.notice("\(String(describing: message.body), privacy: .public)")
    }
}

/// Logs page load results so a blank window can be diagnosed from the unified log.
final class NavigationLog: NSObject, WKNavigationDelegate {
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        pageLogger.notice("loaded \(webView.url?.absoluteString ?? "?", privacy: .public)")
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        pageLogger.error("load failed: \(error.localizedDescription, privacy: .public)")
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!,
                 withError error: Error) {
        pageLogger.error("load failed: \(error.localizedDescription, privacy: .public)")
    }

    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        pageLogger.error("web content process terminated")
    }
}
