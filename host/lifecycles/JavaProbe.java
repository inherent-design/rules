import java.nio.file.*;
import java.math.BigInteger;
import java.util.concurrent.*;

class JavaProbe {
    static void row(String feature, String predicate, String observed, int result) {
        System.out.printf("{\"v\":2,\"profile\":\"java-%s\",\"app\":\"jvm-candidate\",\"feature\":\"%s\",\"operationId\":\"%s\",\"target\":\"fixture/document\",\"basis\":\"1\",\"predicate\":\"%s\",\"observed\":{%s},\"outcome\":{\"decision\":%d}}%n",
            System.getProperty("java.runtime.version")+"-"+System.getProperty("os.name")+"-"+System.getProperty("os.arch"),feature,feature,predicate,observed,result);
    }
    public static void main(String[] args) throws Exception {
        var root=Files.createTempDirectory("rules-lifecycle-jdk-");
        var file=root.resolve("document");
        var started=new CountDownLatch(1);
        var release=new CountDownLatch(1);
        var executor=Executors.newSingleThreadExecutor();
        try {
            Files.writeString(file,"original");
            long captured=1;
            var save=executor.submit(()->{
                started.countDown();
                if(!release.await(3,TimeUnit.SECONDS)) throw new AssertionError("gate");
                Files.writeString(file,"revision-1");
                return captured;
            });
            if(!started.await(3,TimeUnit.SECONDS)) throw new AssertionError("worker start");
            long current=2; // A later user edit while the first revision is still being written.
            row("close-while-writing","retire","\"closed\":true,\"end_confirmed\":false",save.isDone()?1:0);
            release.countDown();
            long acknowledged=save.get(3,TimeUnit.SECONDS);
            if(!Files.readString(file).equals("revision-1")) throw new AssertionError("wrong saved bytes");
            row("save-old-revision","save_status","\"confirmed\":true,\"newer_edit\":true",current!=acknowledged?1:0);
            row("save-retired","retire","\"closed\":true,\"end_confirmed\":true",save.isDone()?1:0);
            // Revision strings survive codec boundaries without host numeric narrowing.
            var basis=new BigInteger("9007199254740993");
            var another=new BigInteger("9007199254740992");
            row("exact-revision-identity","consume","\"identity\":false,\"compatible\":true,\"covered\":true",basis.equals(another)?1:0);
            if(!new BigInteger(basis.toString()).equals(basis))throw new AssertionError("round trip");
        } finally {
            release.countDown();executor.shutdownNow();
            if(!executor.awaitTermination(3,TimeUnit.SECONDS))throw new AssertionError("executor still live");
            Files.deleteIfExists(file);Files.delete(root);
        }
    }
}
