import CoreGraphics
import Foundation

/// Window placement and behaviour, read from the "window" section of display.json.
public struct WindowSettings: Equatable, Decodable, Sendable {
    public enum Corner: String, Decodable, Sendable { case topLeft, topRight, bottomLeft, bottomRight }

    /// front: always on top. normal: like other windows. back: stays behind other windows.
    public enum Level: String, Decodable, Sendable { case front, normal, back }

    public var width: Double
    public var height: Double
    public var corner: Corner
    public var margin: Double
    public var level: Level

    /// A small window at the screen edge by default.
    public init(width: Double = 240, height: Double = 320, corner: Corner = .bottomRight,
                margin: Double = 24, level: Level = .front) {
        self.width = width
        self.height = height
        self.corner = corner
        self.margin = margin
        self.level = level
    }

    enum CodingKeys: String, CodingKey { case width, height, corner, margin, level }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let d = WindowSettings()
        self.init(
            width: try c.decodeIfPresent(Double.self, forKey: .width) ?? d.width,
            height: try c.decodeIfPresent(Double.self, forKey: .height) ?? d.height,
            corner: try c.decodeIfPresent(Corner.self, forKey: .corner) ?? d.corner,
            margin: try c.decodeIfPresent(Double.self, forKey: .margin) ?? d.margin,
            level: try c.decodeIfPresent(Level.self, forKey: .level) ?? d.level
        )
    }

    public static func fromDisplayJSON(_ data: Data) throws -> WindowSettings {
        struct Display: Decodable { var window: WindowSettings? }
        return try JSONDecoder().decode(Display.self, from: data).window ?? WindowSettings()
    }

    /// Window frame inside a screen's visible frame (AppKit coordinates, origin bottom-left).
    public func frame(in visible: CGRect) -> CGRect {
        let left = corner == .topLeft || corner == .bottomLeft
        let top = corner == .topLeft || corner == .topRight
        let x = left ? visible.minX + margin : visible.maxX - margin - width
        let y = top ? visible.maxY - margin - height : visible.minY + margin
        return CGRect(x: x, y: y, width: width, height: height)
    }
}
