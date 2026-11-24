import ADRIACore
import Foundation
import WebKit

/// Serves the bundled web app at adria://app/... and allowlisted ADRIA_HOME
/// files at adria://app/home/... . Nothing else on disk is reachable.
final class AppSchemeHandler: NSObject, WKURLSchemeHandler {
    static let scheme = "adria"
    private let webRoot: URL
    private let home: URL

    init(webRoot: URL, home: URL) {
        self.webRoot = webRoot.standardizedFileURL
        self.home = home
    }

    func webView(_ webView: WKWebView, start task: any WKURLSchemeTask) {
        guard let url = task.request.url else { return }
        let path = String(url.path.drop(while: { $0 == "/" }))
        let file: URL?
        var noStore = false
        if path.hasPrefix("home/") {
            file = HomeFiles.resolve(String(path.dropFirst("home/".count)), home: home)
            noStore = true
        } else {
            let candidate = webRoot.appendingPathComponent(path).standardizedFileURL
            file = candidate.path.hasPrefix(webRoot.path + "/") ? candidate : nil
        }
        guard let file, let data = try? Data(contentsOf: file) else {
            task.didReceive(HTTPURLResponse(url: url, statusCode: 404, httpVersion: "HTTP/1.1", headerFields: [:])!)
            task.didFinish()
            return
        }
        var headers = ["Content-Type": Self.mimeType(file.pathExtension), "Content-Length": "\(data.count)"]
        if noStore { headers["Cache-Control"] = "no-store" }
        task.didReceive(HTTPURLResponse(url: url, statusCode: 200, httpVersion: "HTTP/1.1", headerFields: headers)!)
        task.didReceive(data)
        task.didFinish()
    }

    func webView(_ webView: WKWebView, stop task: any WKURLSchemeTask) {}

    private static func mimeType(_ ext: String) -> String {
        switch ext {
        case "html": return "text/html; charset=utf-8"
        case "js": return "text/javascript; charset=utf-8"
        case "css": return "text/css; charset=utf-8"
        case "json", "": return "application/json"
        default: return "application/octet-stream"
        }
    }
}
