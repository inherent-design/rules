package study.minecraft;

import com.google.gson.*;
import java.lang.reflect.*;
import java.nio.channels.SeekableByteChannel;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.*;

/** Original linked-filesystem APIs over owned byte canaries,never a game/renderer. */
public final class LinkFSProbe {
    private LinkFSProbe() { }
    private interface Action { JsonElement run() throws Exception; }
    private static final JsonArray rows=new JsonArray();
    private static int observerErrors;
    private static void event(String id,String domain,Action action) {
        JsonObject row=new JsonObject();row.addProperty("id",id);row.addProperty("domain",domain);
        try {row.add("value",action.run());}
        catch(Throwable error) {
            while(error instanceof InvocationTargetException&&error.getCause()!=null)error=error.getCause();
            row.addProperty("error",error.getClass().getSimpleName());
            if(error instanceof LinkageError||error instanceof ReflectiveOperationException)observerErrors++;
        }
        rows.add(row);
    }
    private static JsonElement bool(boolean value) {return new JsonPrimitive(value);}
    private static JsonElement read(Path path) throws Exception {return new JsonPrimitive(Files.readString(path));}
    private static JsonElement listing(Path path) throws Exception {
        List<String> names=new ArrayList<>();
        try(DirectoryStream<Path> stream=Files.newDirectoryStream(path)) {
            for(Path child:stream)names.add(child.getFileName().toString());
        }
        Collections.sort(names);return new Gson().toJsonTree(names);
    }
    public static void main(String[] args) throws Exception {
        if(args.length!=3)throw new IllegalArgumentException("Supply bindings,owned fixture root,and output.");
        JsonObject binding=JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();
        JsonObject f=binding.getAsJsonObject("fs"),b=binding.getAsJsonObject("builder");
        Class<?> fsType=Class.forName(f.get("class").getAsString()),builderType=Class.forName(b.get("class").getAsString());
        Method builder=fsType.getDeclaredMethod(f.getAsJsonObject("methods").get("builder").getAsString());
        Method put=builderType.getDeclaredMethod(b.getAsJsonObject("methods").get("put").getAsString(),List.class,Path.class);
        Method build=builderType.getDeclaredMethod(b.getAsJsonObject("methods").get("build").getAsString(),String.class);
        builder.setAccessible(true);put.setAccessible(true);build.setAccessible(true);
        Path root=Path.of(args[1]);Files.createDirectory(root);
        Path physical=root.resolve("backing"),absent=root.resolve("absent");Files.writeString(physical,"A");
        Object first=builder.invoke(null),second=builder.invoke(null);
        put.invoke(first,List.of("assets","a"),physical);put.invoke(first,List.of("alias"),physical);put.invoke(first,List.of("ghost"),absent);
        put.invoke(second,List.of("assets","a"),physical);
        FileSystem fs=(FileSystem)build.invoke(first,"same-label"),other=(FileSystem)build.invoke(second,"same-label");
        Path a=fs.getPath("/assets/a"),alias=fs.getPath("/alias"),ghost=fs.getPath("/ghost"),missing=fs.getPath("/missing"),relative=fs.getPath("assets/a");
        try {
            event("initial-open","virtual",()->bool(fs.isOpen()));
            event("initial-readonly","virtual",()->bool(fs.isReadOnly()));
            event("same-logical-path","provider",()->bool(fs.provider().isSameFile(a,a)));
            event("different-logical-shared-backing","provider",()->bool(fs.provider().isSameFile(a,alias)));
            event("files-api-shared-backing","library",()->bool(Files.isSameFile(a,alias)));
            event("different-filesystem-same-label","provider",()->bool(fs.provider().isSameFile(a,other.getPath("/assets/a"))));
            event("same-missing-logical-path","provider",()->bool(fs.provider().isSameFile(missing,missing)));
            event("mapped-existing","virtual",()->bool(Files.exists(a)));
            event("mapped-missing-backing-existing","virtual",()->bool(Files.exists(ghost)));
            event("unmapped-existing","virtual",()->bool(Files.exists(missing)));
            event("relative-existing","virtual",()->bool(Files.exists(relative)));
            event("relative-read","read",()->read(relative));
            event("initial-read","read",()->read(a));
            event("ghost-read","read",()->read(ghost));
            event("metadata-size","attributes",()->new JsonPrimitive(Files.readAttributes(a,BasicFileAttributes.class).size()));
            event("root-list","virtual",()->listing(fs.getPath("/")));
            Object key=Files.readAttributes(physical,BasicFileAttributes.class).fileKey();
            Files.writeString(physical,"B");
            event("backing-write-key-stability","owned-control",()->{
                Object after=Files.readAttributes(physical,BasicFileAttributes.class).fileKey();
                return key==null||after==null?JsonNull.INSTANCE:bool(key.equals(after));
            });
            event("read-after-backing-write","read",()->read(alias));
            Files.delete(physical);
            event("mapped-existing-after-delete","virtual",()->bool(Files.exists(a)));
            event("read-after-backing-delete","read",()->read(a));
            event("write-open","provider",()->{
                try(SeekableByteChannel channel=Files.newByteChannel(a,Set.of(StandardOpenOption.WRITE))) {
                    return bool(channel.isOpen());
                }
            });
            fs.close();
            event("open-after-close","virtual",()->bool(fs.isOpen()));
            Files.writeString(physical,"A");
            event("read-after-close-and-restore","read",()->read(a));
        } finally {
            Files.writeString(physical,"A");fs.close();other.close();
        }
        JsonObject output=new JsonObject();output.addProperty("schema",1);output.addProperty("observerErrors",observerErrors);
        output.addProperty("ownedOriginalBytesRestored",Files.readString(physical).equals("A"));output.add("rows",rows);
        Files.writeString(Path.of(args[2]),new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create().toJson(output)+"\n");
        System.out.println("Observed "+rows.size()+" linked-filesystem API/control snapshots;no game or renderer.");
    }
}
