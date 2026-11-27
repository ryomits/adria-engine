import CoreGraphics
import Testing
@testable import ADRIACore

struct PointerGestureTests {
    @Test func pressAndReleaseInPlaceIsAClick() {
        var g = PointerGesture(down: CGPoint(x: 100, y: 100), windowOrigin: .zero)
        _ = g.moved(to: CGPoint(x: 101, y: 102))
        #expect(g.isClick)
    }

    @Test func movingPastTheThresholdIsADrag() {
        var g = PointerGesture(down: CGPoint(x: 100, y: 100), windowOrigin: .zero)
        _ = g.moved(to: CGPoint(x: 110, y: 100))
        #expect(!g.isClick)
    }

    @Test func aDragStaysADragWhenItComesBack() {
        var g = PointerGesture(down: CGPoint(x: 100, y: 100), windowOrigin: .zero)
        _ = g.moved(to: CGPoint(x: 120, y: 100))
        _ = g.moved(to: CGPoint(x: 100, y: 100))
        #expect(!g.isClick)
    }

    @Test func smallJitterDoesNotMoveTheWindow() {
        var g = PointerGesture(down: CGPoint(x: 100, y: 100), windowOrigin: CGPoint(x: 500, y: 40))
        #expect(g.moved(to: CGPoint(x: 102, y: 101)) == nil)
    }

    @Test func dragMovesTheWindowByThePointerDelta() {
        var g = PointerGesture(down: CGPoint(x: 100, y: 100), windowOrigin: CGPoint(x: 500, y: 40))
        #expect(g.moved(to: CGPoint(x: 80, y: 130)) == CGPoint(x: 480, y: 70))
    }
}
