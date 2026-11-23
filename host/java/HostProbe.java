import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.concurrent.*;

class HostProbe {
    // Fixed fixture names only. Write observations in the same v1 representation as the POSIX probe.
    static void row(String surface, String name, int result, String[] fields, boolean... values) {
        var facts = new java.util.StringJoiner(",");
        for (int i = 0; i < fields.length; i++) facts.add("\"" + fields[i] + "\":" + values[i]);
        System.out.printf("{\"v\":1,\"surface\":\"%s\",\"case\":\"%s\",\"observed\":{%s},\"outcome\":{\"decision\":%d}}%n",
                surface, name, facts, result);
    }

    static void files() throws Exception {
        var dir = Files.createTempDirectory("rules-jdk-");
        var live = dir.resolve("live");
        var stage = dir.resolve("stage");
        try {
            Files.writeString(live, "A");
            Files.writeString(stage, "B");
            try (var old = Files.newInputStream(live)) {
                Files.move(stage, live, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
                var fields = new String[]{"opened_before","replaced"};
                row("file", "jdk-held", old.read() - 'A', fields, true, true);
                row("file", "jdk-fresh", Files.readAllBytes(live)[0] - 'A', fields, false, true);
            }
        } finally {
            Files.deleteIfExists(stage);
            Files.deleteIfExists(live);
            Files.delete(dir);
        }
    }

    static void work(ExecutorService executor) throws Exception {
        var started = new CountDownLatch(1);
        var release = new CountDownLatch(1);
        var retired = new CountDownLatch(1);
        var progress = new java.util.concurrent.atomic.AtomicInteger();
        try {
            var job = executor.submit(() -> {
                started.countDown();
                try {
                    release.await();
                    progress.incrementAndGet();
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                } finally {
                    retired.countDown();
                }
            });
            if (!started.await(3, TimeUnit.SECONDS)) throw new AssertionError("worker never started");
            // Stop waiting on this Future without interrupting the running computation.
            if (!job.cancel(false) || !job.isDone()) throw new AssertionError("fixture did not cancel its Future");
            var fields = new String[]{"requested_stop","witnessed_end"};
            row("work", "jdk-future-done-worker-blocked", progress.get(), fields, true, false);
            release.countDown();
            if (!retired.await(3, TimeUnit.SECONDS)) throw new AssertionError("worker never retired");
            row("work", "jdk-worker-retired", progress.get(), fields, true, true);
        } finally {
            release.countDown();
            executor.shutdownNow();
            if (!executor.awaitTermination(3, TimeUnit.SECONDS)) throw new AssertionError("executor still active");
        }
    }

    static void network() throws Exception {
        for (boolean acknowledge : new boolean[]{false,true}) {
            try (var server = new ServerSocket(0, 1, InetAddress.getLoopbackAddress());
                 var client = new Socket(server.getInetAddress(),server.getLocalPort());
                 var peer = server.accept()) {
                client.setSoTimeout(3000);
                peer.setSoTimeout(3000);
                client.getOutputStream().write(7);
                if (peer.getInputStream().read() != 7) throw new AssertionError("request");
                if (acknowledge) peer.getOutputStream().write("1 7 COMMIT\n".getBytes(StandardCharsets.US_ASCII));
                peer.shutdownOutput();
                var received = new String(client.getInputStream().readAllBytes(),StandardCharsets.US_ASCII);
                row("receipt","jdk-" + (acknowledge ? "ack" : "eof"), received.equals("1 7 COMMIT\n") ? 2 : 0,
                    new String[]{"id_matches","complete","committed"},acknowledge,acknowledge,acknowledge);
            }
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length > 0 && args[0].equals("console")) {
            System.out.println(System.console() != null);
            System.err.println("diagnostic");
            return;
        }
        files();
        work(Executors.newSingleThreadExecutor());
        network();
    }
}
