// Offscreen blit. World and device generations are application-owned integers.
// The command buffer identity and successful terminal state come from Metal.
import Foundation
import Metal

enum Failure: Error { case noDevice, allocation, command, execution }
guard let device = MTLCreateSystemDefaultDevice(), let queue = device.makeCommandQueue() else { throw Failure.noDevice }
guard let buffer = device.makeBuffer(length: 4, options: .storageModeShared) else { throw Failure.allocation }
let readback = buffer.contents().assumingMemoryBound(to: UInt8.self)
readback.initialize(repeating: 0, count: 4)
guard let cmd = queue.makeCommandBuffer(), let blit = cmd.makeBlitCommandEncoder() else { throw Failure.command }
blit.fill(buffer: buffer, range: 0..<4, value: 7)
blit.endEncoding()
let capturedWorld = 1
let capturedDevice = device.registryID
func observe(_ world: Int, _ deviceID: UInt64, _ label: String, ready: Bool = true) throws {
    let finished = cmd.status == .completed && cmd.error == nil
    let current = world == capturedWorld && deviceID == capturedDevice
    // Consumer reads the buffer only after this command completes under this basis.
    var published: UInt8?
    if finished && current && ready { published = readback.pointee }
    if let value = published, value != 7 { throw Failure.execution }
    let trace: [String: Any] = ["v":1,"surface":"product","case":label,
        "observed":["owned_completion":finished,"world_current":world == capturedWorld,"device_current":deviceID == capturedDevice,"consumer_ready":ready],
        "outcome":["decision":published != nil ? 2 : (finished ? 1 : 0)]]
    print(String(decoding:try JSONSerialization.data(withJSONObject:trace), as:UTF8.self))
}
try observe(1,capturedDevice,"encoded")
cmd.commit()
cmd.waitUntilCompleted()
guard cmd.status == .completed, cmd.error == nil else { throw Failure.execution }
try observe(1,capturedDevice,"readback")
try observe(2,capturedDevice,"old-world")
try observe(1,capturedDevice ^ 1,"old-device-generation")
try observe(1,capturedDevice,"withdrawn-demand",ready:false)
