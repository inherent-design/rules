// Owner-run Java 25 host API observations. No game, GPU, FFI call or raw pointer.
package study.host;

import java.lang.foreign.Arena;
import java.lang.foreign.MemorySegment;
import java.lang.foreign.ValueLayout;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

public final class ArenaProbe {
    private static final List<String> rows = new ArrayList<>();

    private static String quote(String value) {
        return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }
    private static String observe(String name, String operation, Arena arena,
                                  MemorySegment segment, Thread owner, boolean shared) {
        boolean before = arena.scope().isAlive();
        boolean actorOwner = Thread.currentThread() == owner;
        boolean success = false;
        String error = "";
        Long value = null;
        try {
            switch (operation) {
                case "read" -> value = segment.get(ValueLayout.JAVA_LONG, 0);
                case "write" -> { segment.set(ValueLayout.JAVA_LONG, 0, 99L); value = 99L; }
                case "close" -> arena.close();
                default -> throw new IllegalArgumentException("Unknown fixture operation");
            }
            success = true;
        } catch (RuntimeException failure) {
            error = failure.getClass().getName();
        }
        return "{\"case\":" + quote(name) + ",\"operation\":" + quote(operation)
            + ",\"beforeAlive\":" + before + ",\"afterAlive\":" + arena.scope().isAlive()
            + ",\"actorOwner\":" + actorOwner + ",\"shared\":" + shared
            + ",\"success\":" + success + ",\"exception\":" + quote(error)
            + ",\"value\":" + (value == null ? "null" : value.toString()) + "}";
    }
    private static void owner(String name, String operation, Arena arena,
                              MemorySegment segment, Thread owner, boolean shared) {
        rows.add(observe(name, operation, arena, segment, owner, shared));
    }
    private static void other(String name, String operation, Arena arena,
                              MemorySegment segment, Thread owner, boolean shared) throws InterruptedException {
        AtomicReference<String> result = new AtomicReference<>();
        Thread worker = Thread.ofPlatform().name("owned-arena-probe").unstarted(
            () -> result.set(observe(name, operation, arena, segment, owner, shared)));
        worker.start();
        worker.join(5000);
        if (worker.isAlive()) throw new IllegalStateException("Owned worker did not retire");
        String value = result.get();
        if (value == null) throw new IllegalStateException("Owned worker produced no observation");
        rows.add(value);
    }
    public static void main(String[] args) throws Exception {
        if (args.length != 0) throw new IllegalArgumentException("No input or user paths accepted");
        Thread owner = Thread.currentThread();
        Arena confined = Arena.ofConfined();
        try {
            MemorySegment segment = confined.allocate(ValueLayout.JAVA_LONG);
            segment.set(ValueLayout.JAVA_LONG, 0, 42L);
            owner("confined-owner-read", "read", confined, segment, owner, false);
            other("confined-other-read", "read", confined, segment, owner, false);
            other("confined-other-close", "close", confined, segment, owner, false);
            owner("confined-owner-read-after-refusal", "read", confined, segment, owner, false);
            owner("confined-owner-close", "close", confined, segment, owner, false);
            owner("confined-owner-read-closed", "read", confined, segment, owner, false);
            owner("confined-owner-close-again", "close", confined, segment, owner, false);
        } finally {
            if (confined.scope().isAlive()) confined.close();
        }
        Arena shared = Arena.ofShared();
        try {
            MemorySegment segment = shared.allocate(ValueLayout.JAVA_LONG);
            segment.set(ValueLayout.JAVA_LONG, 0, 42L);
            other("shared-other-write", "write", shared, segment, owner, true);
            owner("shared-owner-read-after-join", "read", shared, segment, owner, true);
            other("shared-other-close", "close", shared, segment, owner, true);
            owner("shared-owner-read-closed", "read", shared, segment, owner, true);
        } finally {
            if (shared.scope().isAlive()) shared.close();
        }
        System.out.println("{\"schema\":1,\"events\":[" + String.join(",", rows) + "]}");
    }
}
