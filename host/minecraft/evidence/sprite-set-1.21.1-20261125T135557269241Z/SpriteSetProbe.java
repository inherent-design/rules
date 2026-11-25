package study.minecraft;

import com.google.gson.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;

/** Original mutable sprite-set methods; constructor-bypassed sprite identities only. */
public final class SpriteSetProbe {
    private SpriteSetProbe() { }
    private static Class<?> setClass;
    private static Method bind, frame, first;
    private static Field sprites;
    private static final IdentityHashMap<Object,Integer> ids = new IdentityHashMap<>();
    private static final Object[] values = new Object[4];
    private static JsonArray labels(List<?> list) {
        JsonArray out=new JsonArray();
        for(Object value:list) {
            if(value==null)out.add(0);
            else {Integer id=ids.get(value);if(id==null)throw new IllegalStateException("Unknown fixture identity");out.add(id);}
        }
        return out;
    }
    private static Throwable unwrap(Throwable t) {
        while(t instanceof InvocationTargetException)t=t.getCause();return t;
    }
    public static void main(String[] args) throws Exception {
        JsonObject bindings=JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();
        JsonObject b=bindings.getAsJsonObject("set");setClass=Class.forName(b.get("class").getAsString());
        JsonObject methods=b.getAsJsonObject("methods");
        bind=setClass.getDeclaredMethod(methods.get("bind").getAsString(),List.class);bind.setAccessible(true);
        frame=setClass.getDeclaredMethod(methods.get("frame").getAsString(),int.class,int.class);frame.setAccessible(true);
        if(methods.has("first")){first=setClass.getDeclaredMethod(methods.get("first").getAsString());first.setAccessible(true);}
        sprites=setClass.getDeclaredField(b.getAsJsonObject("fields").get("sprites").getAsString());sprites.setAccessible(true);
        Constructor<?> ctor=setClass.getDeclaredConstructor();ctor.setAccessible(true);
        Class<?> unsafeClass=Class.forName("sun.misc.Unsafe");Field f=unsafeClass.getDeclaredField("theUnsafe");f.setAccessible(true);Object unsafe=f.get(null);
        Method allocate=unsafeClass.getMethod("allocateInstance",Class.class);
        Class<?> spriteClass=Class.forName(bindings.getAsJsonObject("sprite").get("class").getAsString());
        for(int i=1;i<=3;i++){values[i]=allocate.invoke(unsafe,spriteClass);ids.put(values[i],i);}
        JsonObject request=JsonParser.parseString(Files.readString(Path.of(args[1]))).getAsJsonObject();
        JsonArray rows=new JsonArray();int errors=0, originalCalls=0;
        for(JsonElement c:request.getAsJsonArray("cases")) {
            JsonObject item=c.getAsJsonObject();Object set=ctor.newInstance();List<Object> input=null;int ordinal=0;
            for(JsonElement s:item.getAsJsonArray("steps")) {
                JsonObject step=s.getAsJsonObject();String op=step.get("op").getAsString();
                if(step.has("modernOnly") && first==null)continue;
                Object result=null;String error="NONE";boolean unexpected=false;
                try {
                    switch(op) {
                        case "bind" -> {input=new ArrayList<>();for(JsonElement v:step.getAsJsonArray("values"))input.add(values[v.getAsInt()]);originalCalls++;bind.invoke(set,input);}
                        case "bindNull" -> {input=null;originalCalls++;bind.invoke(set,new Object[]{null});}
                        case "mutate" -> input.set(step.get("index").getAsInt(),values[step.get("value").getAsInt()]);
                        case "frame" -> {originalCalls++;result=frame.invoke(set,step.get("index").getAsInt(),step.get("max").getAsInt());}
                        case "first" -> {originalCalls++;result=first.invoke(set);}
                        default -> throw new IllegalStateException(op);
                    }
                } catch(ReflectiveOperationException e) {
                    Throwable t=unwrap(e);error=t.getClass().getName();
                    unexpected=!(t instanceof NullPointerException || t instanceof ArithmeticException || t instanceof IndexOutOfBoundsException || t instanceof NoSuchElementException);
                    if(unexpected)errors++;
                }
                List<?> bound=(List<?>)sprites.get(set);JsonObject row=new JsonObject();
                row.addProperty("case",item.get("id").getAsString());row.addProperty("ordinal",ordinal++);row.add("step",step);
                row.addProperty("error",error);row.addProperty("unexpected",unexpected);row.addProperty("selected",result==null?0:ids.get(result));
                row.add("bound",bound==null?JsonNull.INSTANCE:labels(bound));row.add("input",input==null?JsonNull.INSTANCE:labels(input));rows.add(row);
            }
        }
        JsonObject out=new JsonObject();out.addProperty("schema",1);out.addProperty("observerErrors",errors);out.addProperty("firstAvailable",first!=null);
        out.addProperty("originalCalls",originalCalls);out.addProperty("identityAdapter","Unsafe.allocateInstance on original sprite class; fields/constructor/render methods unused");out.add("rows",rows);
        Files.writeString(Path.of(args[2]),new GsonBuilder().serializeNulls().setPrettyPrinting().disableHtmlEscaping().create().toJson(out)+"\n");
        System.out.println("Recorded "+rows.size()+" sprite-set boundaries; originalCalls="+originalCalls+"; observerErrors="+errors);
        if(errors!=0)System.exit(2);
    }
}
