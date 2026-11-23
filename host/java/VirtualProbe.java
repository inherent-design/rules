// Compile once per tested JDK. This extension uses the final Java 21 API.
import java.util.concurrent.Executors;

class VirtualProbe {
    public static void main(String[] args) throws Exception {
        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            if (!executor.submit(() -> Thread.currentThread().isVirtual()).get()) {
                throw new AssertionError("expected a virtual worker");
            }
            HostProbe.work(executor);
        }
    }
}
