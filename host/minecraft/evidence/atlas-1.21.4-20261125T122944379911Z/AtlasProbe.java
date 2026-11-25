package study.minecraft;

import com.google.gson.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;
import java.util.function.Predicate;

/** Original source-list assembly; authored sources/loaders, never image loading. */
public final class AtlasProbe {
    private static JsonObject bindings;
    private AtlasProbe() { }
    private static Class<?> cls(String role) throws ClassNotFoundException { return Class.forName(bindings.getAsJsonObject(role).get("class").getAsString()); }
    private static String method(String role,String signature) { return bindings.getAsJsonObject(role).getAsJsonObject("methods").get(signature).getAsString(); }
    private static Object call(Object target,String role,String signature,Class<?>[] types,Object... args) throws ReflectiveOperationException {
        Method m=cls(role).getDeclaredMethod(method(role,signature),types);m.setAccessible(true);return m.invoke(target,args);
    }
    private static Throwable cause(Throwable t) {
        while (t instanceof InvocationTargetException || t instanceof UndeclaredThrowableException) t=t.getCause();
        return t;
    }
    private static Object objectMethod(Object p,Method m,Object[] args) {
        return switch(m.getName()) {case "hashCode" -> System.identityHashCode(p);case "equals" -> p==args[0];case "toString" -> "authored-atlas-proxy";default -> throw new IllegalStateException(m.toString());};
    }
    private static final class Context {
        final JsonObject input;
        final JsonArray events=new JsonArray();
        final IdentityHashMap<Object,String> labels=new IdentityHashMap<>();
        final Map<String,Object> suppliers=new HashMap<>();
        final Map<String,Integer> discards=new TreeMap<>();
        int sourceRuns;
        Context(JsonObject input) { this.input=input; }
        Object supplier(String label) throws ClassNotFoundException {
            Object old=suppliers.get(label);if(old!=null)return old;
            discards.put(label,0);
            Class<?> c=cls("supplier");
            Object p=Proxy.newProxyInstance(c.getClassLoader(),new Class<?>[]{c},(proxy,m,args)->{
                if(m.getDeclaringClass()==Object.class)return objectMethod(proxy,m,args);
                if((args==null || args.length==0) && m.getName().equals(method("supplier","discard()"))) {
                    discards.put(label,discards.get(label)+1);events.add("discard:"+label);
                    if(input.getAsJsonArray("throwDiscard").asList().stream().anyMatch(v->v.getAsString().equals(label)))throw new IllegalStateException("authored-discard:"+label);
                    return null;
                }
                throw new IllegalStateException("Unselected supplier invocation:"+m.getName());
            });
            suppliers.put(label,p);labels.put(p,label);return p;
        }
        Object source(JsonArray actions,int index) throws ClassNotFoundException {
            Class<?> c=cls("source");return Proxy.newProxyInstance(c.getClassLoader(),new Class<?>[]{c},(proxy,m,args)->{
                if(m.getDeclaringClass()==Object.class)return objectMethod(proxy,m,args);
                if(!m.getName().equals(method("source","run")) || args==null || args.length!=2)throw new IllegalStateException("Unselected source invocation");
                sourceRuns++;events.add("source:"+index);
                for(JsonElement element:actions) {
                    JsonObject action=element.getAsJsonObject();String op=action.get("op").getAsString();events.add("action:"+op);
                    try {
                        switch(op) {
                            case "add" -> {
                                Object id=call(null,"id","parse",new Class<?>[]{String.class},action.get("id").getAsString());
                                call(args[1],"output","add",new Class<?>[]{cls("id"),cls("supplier")},id,supplier(action.get("supplier").getAsString()));
                            }
                            case "remove" -> {
                                String prefix=action.get("prefix").getAsString();Predicate<Object> predicate=id->id.toString().startsWith(prefix);
                                call(args[1],"output","removeAll",new Class<?>[]{Predicate.class},predicate);
                            }
                            case "fail" -> throw new IllegalStateException("authored-source-failure");
                            default -> throw new IllegalArgumentException(op);
                        }
                    } catch(ReflectiveOperationException | IllegalStateException e) {
                        Throwable t=cause(e);events.add("error:"+t.getMessage());
                        if(!action.has("catch") || !action.get("catch").getAsBoolean())throw t;
                        events.add("caught");
                    }
                }
                return null;
            });
        }
        JsonObject run() throws Exception {
            List<Object> sources=new ArrayList<>();int index=0;
            for(JsonElement source:input.getAsJsonArray("sources"))sources.add(source(source.getAsJsonArray(),index++));
            Constructor<?> c=cls("list").getDeclaredConstructor(List.class);c.setAccessible(true);Object owner=c.newInstance(sources);
            JsonObject result=new JsonObject();result.addProperty("case",input.get("id").getAsString());
            JsonArray retained=new JsonArray();boolean returned=false;int defaultCount=0;String error="NONE";
            try {
                List<?> loaders=(List<?>)call(owner,"list","list",new Class<?>[]{cls("resources")},new Object[]{null});
                returned=true;
                if(loaders.isEmpty() || labels.containsKey(loaders.get(0)))throw new IllegalStateException("Missing authored-boundary default loader");
                for(Object loader:loaders) { String label=labels.get(loader);if(label==null)defaultCount++;else retained.add(label); }
                if(defaultCount!=1)throw new IllegalStateException("Unexpected unowned loader count");
            } catch(InvocationTargetException e) { error=cause(e).toString(); }
            result.addProperty("returned",returned);result.addProperty("defaultLoaders",defaultCount);result.addProperty("error",error);
            result.addProperty("sourceRuns",sourceRuns);result.add("retained",retained);result.add("discards",new Gson().toJsonTree(discards));result.add("events",events);
            return result;
        }
    }
    public static void main(String[] args) throws Exception {
        bindings=JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();
        JsonObject request=JsonParser.parseString(Files.readString(Path.of(args[1]))).getAsJsonObject();JsonArray cases=new JsonArray();int errors=0;
        for(JsonElement element:request.getAsJsonArray("cases")) {
            JsonObject row=new Context(element.getAsJsonObject()).run();cases.add(row);String error=row.get("error").getAsString();
            if(!error.equals("NONE") && !error.equals("java.lang.IllegalStateException: authored-source-failure") && !error.matches("java.lang.IllegalStateException: authored-discard:[ABC]"))errors++;
        }
        JsonObject output=new JsonObject();output.addProperty("schema",1);output.addProperty("observerErrors",errors);output.add("cases",cases);
        Files.writeString(Path.of(args[2]),new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create().toJson(output)+"\n");
        System.out.println("Observed "+cases.size()+" original source-list cases;observerErrors="+errors+";no loader invoked");
        if(errors!=0)System.exit(2);
    }
}
