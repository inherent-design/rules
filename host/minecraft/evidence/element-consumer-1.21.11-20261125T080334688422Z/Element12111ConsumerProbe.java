// Controlled original CPU bake boundary. Texture resolution is intercepted, not executed.
package study.minecraft;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public final class Element12111ConsumerProbe {
    private final JsonObject bindings;
    private Element12111ConsumerProbe(JsonObject b) { bindings=b; }
    private Class<?> type(String role) throws ReflectiveOperationException { return Class.forName(bindings.getAsJsonObject(role).get("class").getAsString()); }
    private Object construct(String role) throws ReflectiveOperationException {
        Constructor<?> c=type(role).getDeclaredConstructor();c.setAccessible(true);return c.newInstance();
    }
    private String getter(String role,String name) { return bindings.getAsJsonObject(role).getAsJsonObject("getters").get(name).getAsString(); }
    private static final class ResolutionIntercepted extends RuntimeException {
        private static final long serialVersionUID=1L;
    }
    public static void main(String[] args) throws Exception {
        if(args.length!=3) throw new IllegalArgumentException("Supply frozen bindings,requests,output");
        var p=new Element12111ConsumerProbe(JsonParser.parseString(Files.readString(Path.of(args[0]),StandardCharsets.UTF_8)).getAsJsonObject());
        Gson gson=new GsonBuilder().registerTypeAdapter(p.type("element"),p.construct("elementDeserializer"))
            .registerTypeAdapter(p.type("face"),p.construct("faceDeserializer")).create();
        Class<?> baker=p.type("baker"),sprites=p.type("sprites");
        if(!baker.isInterface() || !sprites.isInterface()) throw new IllegalStateException("Selected adapters require original interfaces");
        Method bake=p.type("geometry").getDeclaredMethod(p.bindings.getAsJsonObject("geometry").get("bakeMethod").getAsString(),
            List.class,p.type("textures"),baker,p.type("state"),p.type("debug"));bake.setAccessible(true);
        JsonArray result=new JsonArray();int errors=0;
        JsonObject request=JsonParser.parseString(Files.readString(Path.of(args[1]),StandardCharsets.UTF_8)).getAsJsonObject();
        for(JsonElement value:request.getAsJsonArray("cases")) {
            JsonObject input=value.getAsJsonObject(),row=new JsonObject();row.add("case",input.get("id"));row.add("input",input.get("input").deepCopy());
            List<String> calls=new ArrayList<>();
            Object spriteProxy=Proxy.newProxyInstance(sprites.getClassLoader(),new Class<?>[]{sprites},(proxy,method,arguments)->{
                if(!method.getName().equals(p.bindings.getAsJsonObject("sprites").get("resolveMethod").getAsString())) throw new IllegalStateException("Unselected sprite adapter call");
                calls.add("resolveSlot");throw new ResolutionIntercepted();
            });
            Object bakerProxy=Proxy.newProxyInstance(baker.getClassLoader(),new Class<?>[]{baker},(proxy,method,arguments)->{
                if(!method.getName().equals(p.getter("baker","sprites"))) throw new IllegalStateException("Unselected baker adapter call");
                calls.add("sprites");return spriteProxy;
            });
            try {
                Object element=gson.fromJson(input.get("input"),p.type("element"));row.addProperty("decoded",true);
                try {
                    Object quads=bake.invoke(null,List.of(element),null,bakerProxy,null,null);
                    Method all=quads.getClass().getDeclaredMethod(p.getter("quads","getAll"));all.setAccessible(true);
                    row.addProperty("outcome","returned");row.addProperty("quads",((List<?>)all.invoke(quads)).size());
                } catch(InvocationTargetException failure) {
                    Throwable cause=failure.getCause();
                    if(cause instanceof ResolutionIntercepted) row.addProperty("outcome","lookup-intercepted");
                    else {
                        row.addProperty("outcome","consumer-exception");row.addProperty("exception",cause.getClass().getName());row.addProperty("message",cause.getMessage());
                        if(cause.getStackTrace().length>0) row.addProperty("topClass",cause.getStackTrace()[0].getClassName());
                        if(!(cause instanceof NullPointerException)) {row.addProperty("observerError",true);errors++;}
                    }
                }
            } catch(ReflectiveOperationException|LinkageError|RuntimeException failure) {
                row.addProperty("observerError",true);row.addProperty("exception",failure.getClass().getName());row.addProperty("message",failure.getMessage());errors++;
            }
            JsonArray prefix=new JsonArray();for(String call:calls)prefix.add(call);row.add("adapterCalls",prefix);result.add(row);
        }
        JsonObject output=new JsonObject();output.addProperty("schema",1);output.addProperty("observerErrors",errors);output.add("cases",result);
        Files.writeString(Path.of(args[2]),output.toString()+"\n",StandardCharsets.UTF_8);System.out.println("cases="+result.size()+" observerErrors="+errors);
        if(errors!=0)System.exit(3);
    }
}
