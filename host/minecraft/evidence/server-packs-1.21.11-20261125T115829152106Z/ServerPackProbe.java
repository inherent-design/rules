package study.minecraft;

import com.google.gson.*;
import java.lang.reflect.*;
import java.net.URI;
import java.nio.file.*;
import java.util.*;
import java.util.function.Consumer;

/** Original manager with controlled serial callbacks. No connection, HTTP or pack reader. */
public final class ServerPackProbe {
    private static JsonObject bindings;
    private static final UUID ID = new UUID(0, 1);
    private ServerPackProbe() { }
    private static Class<?> cls(String role) throws ClassNotFoundException {
        return Class.forName(bindings.getAsJsonObject(role).get("class").getAsString());
    }
    private static String fieldName(String role, String field) {
        return bindings.getAsJsonObject(role).getAsJsonObject("fields").get(field).getAsString();
    }
    private static Object field(Object o, String role, String field) throws ReflectiveOperationException {
        Field f = cls(role).getDeclaredField(fieldName(role, field)); f.setAccessible(true); return f.get(o);
    }
    private static Object call(Object o, String role, String signature, Class<?>[] types, Object... args) throws ReflectiveOperationException {
        String name = bindings.getAsJsonObject(role).getAsJsonObject("methods").get(signature).getAsString();
        Method m = cls(role).getDeclaredMethod(name, types); m.setAccessible(true); return m.invoke(o, args);
    }
    private static Object constant(String role, String name) throws ReflectiveOperationException {
        Field f = cls(role).getDeclaredField(fieldName(role, name)); f.setAccessible(true); return f.get(null);
    }
    private static Object proxy(String role, InvocationHandler handler) throws ClassNotFoundException {
        Class<?> c = cls(role); return Proxy.newProxyInstance(c.getClassLoader(), new Class<?>[]{c}, handler);
    }
    private static String symbol(Object value) { return value == null ? "NONE" : ((Enum<?>)value).name(); }
    private static final class Context {
        Object manager;
        Object reload;
        Consumer<Object> download;
        int schedules;
        int downloads;
        int reloads;
        final List<String> feedback = new ArrayList<>();
        Context(String prompt) throws ReflectiveOperationException {
            Object downloader = proxy("downloader", (p, m, a) -> {
                if (!m.getName().equals(bindings.getAsJsonObject("downloader").getAsJsonObject("methods").get("download(java.util.Map,java.util.function.Consumer)").getAsString())) throw new IllegalStateException(m.toString());
                Map<?,?> requests = (Map<?,?>)a[0];
                if (!requests.keySet().equals(Set.of(ID))) throw new IllegalStateException("Unselected download IDs");
                @SuppressWarnings("unchecked") Consumer<Object> c = (Consumer<Object>)a[1];
                download = c; downloads++; return null;
            });
            Object reporter = proxy("feedback", (p, m, a) -> {
                if (!ID.equals(a[0])) throw new IllegalStateException("Unselected feedback ID");
                feedback.add(symbol(a[1])); return null;
            });
            Object config = proxy("reload", (p, m, a) -> { reload = a[0]; reloads++; return null; });
            Constructor<?> c = cls("manager").getDeclaredConstructor(cls("downloader"), cls("feedback"), cls("reload"), Runnable.class, cls("prompt"));
            c.setAccessible(true);
            manager = c.newInstance(downloader, reporter, config, (Runnable)() -> schedules++, constant("prompt", prompt));
        }
        void act(String action) throws Exception {
            switch (action) {
                case "remote" -> call(manager,"manager","pushPack(java.util.UUID,java.net.URL,com.google.common.hash.HashCode)",new Class<?>[]{UUID.class,java.net.URL.class,Class.forName("com.google.common.hash.HashCode")},ID,URI.create("https://example.invalid/study.zip").toURL(),null);
                case "local" -> call(manager,"manager","pushLocalPack(java.util.UUID,java.nio.file.Path)",new Class<?>[]{UUID.class,Path.class},ID,Path.of("owned-placeholder.zip"));
                case "pop" -> call(manager,"manager","popPack(java.util.UUID)",new Class<?>[]{UUID.class},ID);
                case "allow", "reject", "reset", "tick", "popAll" -> {
                    String method = switch(action) {case "allow" -> "allowServerPacks";case "reject" -> "rejectServerPacks";case "reset" -> "resetPromptStatus";default -> action;};
                    call(manager,"manager",method+"()",new Class<?>[]{});
                }
                case "download-ok", "download-fail" -> {
                    if (download == null) throw new IllegalStateException("No captured download");
                    Constructor<?> c = cls("batch").getDeclaredConstructor(Map.class,Set.class); c.setAccessible(true);
                    Map<UUID,Path> paths = action.equals("download-ok") ? Map.of(ID,Path.of("download-placeholder.zip")) : Map.of();
                    Set<UUID> failed = action.equals("download-fail") ? Set.of(ID) : Set.of();
                    Consumer<Object> callback = download; download = null;
                    callback.accept(c.newInstance(paths,failed));
                }
                case "success", "failure", "recovery-failure" -> {
                    if (reload == null) throw new IllegalStateException("No captured reload");
                    if (action.equals("success")) { call(reload,"callbacks","onSuccess()",new Class<?>[]{}); reload = null; }
                    else { call(reload,"callbacks","onFailure(boolean)",new Class<?>[]{boolean.class},action.equals("recovery-failure")); if (action.equals("recovery-failure")) reload = null; }
                }
                default -> throw new IllegalArgumentException(action);
            }
        }
        JsonObject snapshot() throws ReflectiveOperationException {
            JsonObject s = new JsonObject();
            s.addProperty("prompt",symbol(field(manager,"manager","packPromptStatus")));
            JsonArray records = new JsonArray();
            for (Object data : (List<?>)field(manager,"manager","packs")) {
                if (!ID.equals(field(data,"data","id"))) throw new IllegalStateException("Unknown record ID");
                JsonObject r = new JsonObject();
                for (String f : List.of("downloadStatus","activationStatus","removalReason")) r.addProperty(f,symbol(field(data,"data",f)));
                r.addProperty("accepted",(Boolean)field(data,"data","promptAccepted"));
                Object path = field(data,"data","path"); r.addProperty("path",path == null ? "NONE" : path.toString()); records.add(r);
            }
            s.add("records",records); s.addProperty("schedules",schedules); s.addProperty("downloads",downloads); s.addProperty("reloads",reloads);
            s.addProperty("downloadCallbackHeld",download != null); s.addProperty("reloadCallbackHeld",reload != null);
            JsonArray toLoad = new JsonArray();
            if (reload != null) for (Object pair : (List<?>)call(reload,"callbacks","packsToLoad()",new Class<?>[]{})) {
                if (!ID.equals(field(pair,"pair","id"))) throw new IllegalStateException("Unknown reload ID");
                toLoad.add(field(pair,"pair","path").toString());
            }
            s.add("toLoad",toLoad); s.add("feedback",new Gson().toJsonTree(feedback)); return s;
        }
    }
    public static void main(String[] args) throws Exception {
        bindings = JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();
        JsonObject request = JsonParser.parseString(Files.readString(Path.of(args[1]))).getAsJsonObject();
        JsonArray rows = new JsonArray(); int errors = 0;
        for (JsonElement element : request.getAsJsonArray("cases")) {
            JsonObject input = element.getAsJsonObject(); Context context = new Context(input.get("prompt").getAsString());
            int index = 0;
            for (JsonElement action : input.getAsJsonArray("actions")) {
                JsonObject row = new JsonObject(); row.addProperty("case",input.get("id").getAsString()); row.addProperty("index",index++);
                row.addProperty("action",action.getAsString()); row.add("before",context.snapshot());
                try { context.act(action.getAsString()); }
                catch (Exception e) { errors++; Throwable t = e instanceof InvocationTargetException ? e.getCause() : e; row.addProperty("error",t.toString()); }
                row.add("after",context.snapshot()); rows.add(row);
            }
        }
        JsonObject output = new JsonObject(); output.addProperty("schema",1); output.addProperty("observerErrors",errors); output.add("rows",rows);
        Files.writeString(Path.of(args[2]),new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create().toJson(output)+"\n");
        System.out.println("Observed "+rows.size()+" original manager actions; errors="+errors);
        if (errors != 0) System.exit(2);
    }
}
