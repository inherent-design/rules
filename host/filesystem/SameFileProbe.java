package study.host;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.BasicFileAttributes;

/** Owner-run standard-library calls only;no application,GUI or daemon. */
public final class SameFileProbe {
    private SameFileProbe() { }
    private static String attributes(Path path) {
        try {
            BasicFileAttributes a=Files.readAttributes(path,BasicFileAttributes.class);
            return a.isDirectory()?"directory":"other";
        } catch (java.io.IOException e) { return e.getClass().getSimpleName(); }
    }
    private static void observe(String name,Path a,Path b) {
        String result;
        try { result=Boolean.toString(Files.isSameFile(a,b)); }
        catch(java.io.IOException e) { result=e.getClass().getSimpleName(); }
        System.out.println(name+"\t"+result+"\t"+attributes(a)+"\t"+attributes(b));
    }
    public static void main(String[] args) throws Exception {
        if(args.length!=1)throw new IllegalArgumentException("Supply one owned fixture root.");
        Path root=Path.of(args[0]);Files.createDirectory(root);
        Path source=root.resolve("source"),other=root.resolve("other");
        Files.createDirectory(source);Files.createDirectory(other);
        observe("existing-equal",source,source);
        observe("existing-different",source,other);
        observe("case-spelling",source,root.resolve("SOURCE"));
        observe("missing-equal",root.resolve("absent"),root.resolve("absent"));
        observe("missing-different",root.resolve("absent"),root.resolve("also-absent"));
    }
}
