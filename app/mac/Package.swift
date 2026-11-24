// swift-tools-version:6.0
import PackageDescription

let package = Package(
    name: "ADRIA",
    platforms: [.macOS(.v14)],
    targets: [
        .target(name: "ADRIACore"),
        .executableTarget(name: "ADRIA", dependencies: ["ADRIACore"]),
        .testTarget(name: "ADRIACoreTests", dependencies: ["ADRIACore"]),
    ]
)
