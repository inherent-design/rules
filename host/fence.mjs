// Inputs are the exact unsigned 64-bit values extracted by a D3D12 adapter.
// The adapter must already have identified the originating device, fence,
// queue signal and its monotonic sequence. A CPU signal on another fence is
// not evidence about this submission.
const removed = (1n << 64n) - 1n;
export function d3d12Fence(value, awaited) {
  for (const n of [value, awaited]) {
    if (typeof n !== 'bigint' || n < 0n || n > removed) throw RangeError('expected exact uint64');
  }
  if (value === removed) return 'device-removed';
  return value >= awaited ? 'reached' : 'pending';
}
