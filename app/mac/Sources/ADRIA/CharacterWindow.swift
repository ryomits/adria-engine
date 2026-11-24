import ADRIACore
import AppKit
import WebKit
import os

let pageLogger = Logger(subsystem: "local.adria.display", category: "page")

/// Borderless, transparent window that shows only the character.
@MainActor
final class CharacterWindow: NSWindow {
    private let schemeHandler: AppSchemeHandler
    private let navigationLog = NavigationLog()

    init(settings: WindowSettings, home: URL, webRoot: URL) {
        schemeHandler = AppSchemeHandler(webRoot: webRoot, home: home)
        let screen = NSScreen.main?.visibleFrame ?? CGRect(x: 0, y: 0, width: 1440, height: 900)
        super.init(contentRect: settings.frame(in: screen), styleMask: [.borderless],
                   backing: .buffered, defer: false)
        isOpaque = false
        backgroundColor = .clear
        hasShadow = false
        isReleasedWhenClosed = false
        ignoresMouseEvents = settings.clickThrough
        // Stay visible on every Space and when other apps are in front.
        collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary, .ignoresCycle]
        level = Self.windowLevel(settings.level)

        let config = WKWebViewConfiguration()
        config.setURLSchemeHandler(schemeHandler, forURLScheme: AppSchemeHandler.scheme)
        config.userContentController.add(PageLog(), name: "log")
        let webView = WKWebView(frame: CGRect(origin: .zero, size: settings.frame(in: screen).size),
                                configuration: config)
        webView.setValue(false, forKey: "drawsBackground")  // transparent page background
        webView.underPageBackgroundColor = .clear
        webView.isInspectable = true  // Safari Web Inspector for local debugging
        webView.autoresizingMask = [.width, .height]
        webView.navigationDelegate = navigationLog
        contentView = webView
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
