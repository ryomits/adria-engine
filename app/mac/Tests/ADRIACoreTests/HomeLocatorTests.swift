import Foundation
import Testing
@testable import ADRIACore

struct HomeLocatorTests {
    @Test func prefersEnvironmentVariable() {
        let url = HomeLocator.locate(environment: ["ADRIA_HOME": "/a"], bundledPath: "/b")
        #expect(url?.path == "/a")
    }

    @Test func fallsBackToPathBundledAtBuildTime() {
        #expect(HomeLocator.locate(environment: [:], bundledPath: "/b\n")?.path == "/b")
    }

    @Test func returnsNilWhenUnknown() {
        #expect(HomeLocator.locate(environment: [:], bundledPath: nil) == nil)
    }
}
