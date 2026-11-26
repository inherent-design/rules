package study.host;

import java.util.ArrayList;
import java.util.List;
import java.util.Timer;
import java.util.TimerTask;
import java.util.concurrent.atomic.AtomicInteger;

/** Own far-future tasks only; no application, GUI, wall-clock, or latency claim. */
public final class TimerProbe {
    private TimerProbe() { }
    private static final long LATER = 86_400_000L;
    private static final AtomicInteger CALLBACKS = new AtomicInteger();
    private static final List<String> EVENTS = new ArrayList<>();

    private static TimerTask task() {
        return new TimerTask() {
            @Override public void run() { CALLBACKS.incrementAndGet(); }
        };
    }

    private static void record(String id, Runnable action) {
        try {
            action.run();
            EVENTS.add("{\"id\":\"" + id + "\",\"error\":0,\"callbacks\":" + CALLBACKS.get() + "}");
        } catch (IllegalStateException e) {
            EVENTS.add("{\"id\":\"" + id + "\",\"error\":1,\"callbacks\":" + CALLBACKS.get() + "}");
        } catch (IllegalArgumentException e) {
            EVENTS.add("{\"id\":\"" + id + "\",\"error\":2,\"callbacks\":" + CALLBACKS.get() + "}");
        }
    }

    private static void booleanEvent(String id, boolean value) {
        EVENTS.add("{\"id\":\"" + id + "\",\"error\":0,\"value\":" + value + ",\"callbacks\":" + CALLBACKS.get() + "}");
    }

    public static void main(String[] args) throws InterruptedException {
        Timer first = new Timer("rules-timer-fixture-first");
        Timer second = new Timer("rules-timer-fixture-second");
        List<Thread> workers = Thread.getAllStackTraces().keySet().stream()
            .filter(t -> t.getName().startsWith("rules-timer-fixture-")).toList();
        if (workers.size() != 2 || workers.stream().anyMatch(Thread::isDaemon))
            throw new IllegalStateException("Expected both owned non-daemon timer threads.");
        try {
            TimerTask neverScheduled = task();
            booleanEvent("cancel-fresh-task", neverScheduled.cancel());
            record("schedule-canceled-task", () -> first.schedule(neverScheduled, LATER));
            TimerTask repeating = task();
            record("schedule-future-task", () -> first.scheduleAtFixedRate(repeating, LATER, LATER));
            record("schedule-same-task-again", () -> first.scheduleAtFixedRate(repeating, LATER, LATER));
            booleanEvent("cancel-scheduled-task", repeating.cancel());
            booleanEvent("cancel-task-again", repeating.cancel());
            record("move-canceled-task-to-new-timer", () -> second.schedule(repeating, LATER));
            TimerTask afterBadDelay = task();
            record("negative-delay", () -> second.schedule(afterBadDelay, -1));
            record("retry-same-task-valid-delay", () -> second.schedule(afterBadDelay, LATER));
            TimerTask afterBadPeriod = task();
            record("zero-period", () -> second.scheduleAtFixedRate(afterBadPeriod, LATER, 0));
            record("retry-same-task-valid-period", () -> second.scheduleAtFixedRate(afterBadPeriod, LATER, LATER));
            record("cancel-first-timer", first::cancel);
            record("cancel-first-timer-again", first::cancel);
            record("fresh-task-on-canceled-timer", () -> first.schedule(task(), LATER));
            record("fresh-task-on-second-timer", () -> second.schedule(task(), LATER));
        } finally {
            first.cancel(); second.cancel();
            for (Thread thread : workers) thread.join(1_000);
        }
        boolean allAbsent = workers.stream().noneMatch(Thread::isAlive);
        booleanEvent("owned-timer-threads-retired", allAbsent);
        if (!allAbsent || CALLBACKS.get() != 0) throw new IllegalStateException("Unexpected worker/callback state.");
        System.out.println("{\"schema\":1,\"java\":\"" + System.getProperty("java.version")
            + "\",\"os\":\"" + System.getProperty("os.name") + "\",\"architecture\":\"" + System.getProperty("os.arch")
            + "\",\"ownedThreads\":2,\"events\":[" + String.join(",", EVENTS) + "]}");
    }
}
