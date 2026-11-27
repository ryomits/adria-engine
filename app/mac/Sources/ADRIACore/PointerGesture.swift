import CoreGraphics

/// Tells a click on the character from a drag that moves the window.
///
/// Points are in screen coordinates. A press that never moves farther than
/// `threshold` points is a click; once past it, the gesture is a drag for good
/// and the window follows the pointer.
public struct PointerGesture: Sendable {
    public static let threshold: CGFloat = 4

    private let down: CGPoint
    private let windowOrigin: CGPoint
    private(set) public var isClick = true

    public init(down: CGPoint, windowOrigin: CGPoint) {
        self.down = down
        self.windowOrigin = windowOrigin
    }

    /// New window origin for a pointer position, or nil while it is still a click.
    public mutating func moved(to point: CGPoint) -> CGPoint? {
        let dx = point.x - down.x
        let dy = point.y - down.y
        if isClick && (dx * dx + dy * dy) <= Self.threshold * Self.threshold {
            return nil
        }
        isClick = false
        return CGPoint(x: windowOrigin.x + dx, y: windowOrigin.y + dy)
    }
}
