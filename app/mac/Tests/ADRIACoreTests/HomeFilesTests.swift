import Foundation
import Testing
@testable import ADRIACore

struct HomeFilesTests {
    let home = URL(fileURLWithPath: "/tmp/adria-home")

    @Test func servesDisplayConfig() {
        #expect(HomeFiles.resolve("display.json", home: home)?.path == "/tmp/adria-home/display.json")
    }

    @Test func servesVRMUnderAvatars() {
        #expect(HomeFiles.resolve("avatars/a.vrm", home: home) != nil)
    }

    @Test func servesSignalFiles() {
        #expect(HomeFiles.resolve("runtime/now_playing", home: home) != nil)
    }

    @Test func refusesPrivateSettings() {
        #expect(HomeFiles.resolve("config.toml", home: home) == nil)
    }

    @Test func refusesPathTraversal() {
        #expect(HomeFiles.resolve("avatars/../config.toml", home: home) == nil)
    }

    @Test func refusesNestedAvatarPaths() {
        #expect(HomeFiles.resolve("avatars/x/../../config.vrm", home: home) == nil)
    }
}
