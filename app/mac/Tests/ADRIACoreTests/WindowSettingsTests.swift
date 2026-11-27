import CoreGraphics
import Foundation
import Testing
@testable import ADRIACore

struct WindowSettingsTests {
    let screen = CGRect(x: 0, y: 0, width: 1920, height: 1080)

    func decode(_ json: String) throws -> WindowSettings {
        try WindowSettings.fromDisplayJSON(Data(json.utf8))
    }

    @Test func usesDefaultsWithoutWindowSection() throws {
        #expect(try decode(#"{"vrm": "a.vrm"}"#) == WindowSettings())
    }

    @Test func defaultWindowIsSmall() {
        #expect(WindowSettings().width * WindowSettings().height <= 300 * 400)
    }

    @Test func readsSize() throws {
        #expect(try decode(#"{"window": {"width": 200, "height": 260}}"#).height == 260)
    }

    @Test func readsLevel() throws {
        #expect(try decode(#"{"window": {"level": "back"}}"#).level == .back)
    }

    @Test func rejectsUnknownLevel() {
        #expect(throws: DecodingError.self) { try decode(#"{"window": {"level": "top"}}"#) }
    }

    @Test func placesWindowInBottomRightCorner() {
        let s = WindowSettings(width: 400, height: 600, corner: .bottomRight, margin: 20)
        #expect(s.frame(in: screen) == CGRect(x: 1500, y: 20, width: 400, height: 600))
    }

    @Test func placesWindowInTopLeftCorner() {
        let s = WindowSettings(width: 400, height: 600, corner: .topLeft, margin: 20)
        #expect(s.frame(in: screen) == CGRect(x: 20, y: 460, width: 400, height: 600))
    }

    @Test func respectsVisibleFrameOrigin() {
        let visible = CGRect(x: 0, y: 80, width: 1920, height: 975)  // Dock at the bottom
        let s = WindowSettings(width: 400, height: 600, corner: .bottomLeft, margin: 0)
        #expect(s.frame(in: visible).origin.y == 80)
    }
}
