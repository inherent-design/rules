package study.minecraft;

import com.google.gson.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;

/** Original weighted selection, with authored weight/preload callbacks. No audio engine. */
public final class SoundProbe {
    private static JsonObject bindings;
    private SoundProbe() { }
    private static Class<?> cls(String role) throws ClassNotFoundException {return Class.forName(bindings.getAsJsonObject(role).get("class").getAsString());}
    private static String name(String role,String key) {return bindings.getAsJsonObject(role).getAsJsonObject("methods").get(key).getAsString();}
    private static Object invoke(Object target,String role,String key,Class<?>[] types,Object... args) throws ReflectiveOperationException {
        Method method=cls(role).getDeclaredMethod(name(role,key),types);method.setAccessible(true);return method.invoke(target,args);
    }
    private static Throwable cause(Throwable e) {
        while(e instanceof InvocationTargetException || e instanceof UndeclaredThrowableException)e=e.getCause();return e;
    }
    private static Object objectMethod(Object p,Method m,Object[] args) {
        return switch(m.getName()){case "hashCode"->System.identityHashCode(p);case "equals"->p==args[0];case "toString"->"authored-weighted-control";default->throw new IllegalStateException(m.toString());};
    }
    private static JsonObject run(JsonObject input) throws Exception {
        JsonArray entries=input.getAsJsonArray("entries"),reads=new JsonArray(),randomCalls=new JsonArray();
        int[] weightsRead=new int[entries.size()],preloads=new int[entries.size()],selected={0};
        Object id=invoke(null,"id","parse",new Class<?>[]{String.class},"fixture:event");
        Constructor<?> constructor=cls("event").getDeclaredConstructor(cls("id"),String.class);constructor.setAccessible(true);Object event=constructor.newInstance(id,null);
        for(int i=0;i<entries.size();i++) {
            final int index=i;JsonObject entry=entries.get(i).getAsJsonObject();JsonArray weights=entry.getAsJsonArray("weights");
            Class<?> weighted=cls("weighted");Object control=Proxy.newProxyInstance(weighted.getClassLoader(),new Class<?>[]{weighted},(p,m,args)->{
                if(m.getDeclaringClass()==Object.class)return objectMethod(p,m,args);
                if(m.getName().equals(name("weighted","weight")) && (args==null || args.length==0)) {
                    int ordinal=weightsRead[index]++;int value=weights.get(Math.min(ordinal,weights.size()-1)).getAsInt();
                    JsonObject read=new JsonObject();read.addProperty("entry",index+1);read.addProperty("ordinal",ordinal);read.addProperty("value",value);reads.add(read);return value;
                }
                if(m.getName().equals(name("weighted","select")) && args!=null && args.length==1) {selected[0]=index+1;return null;}
                if(m.getName().equals(name("weighted","preload")) && args!=null && args.length==1) {
                    preloads[index]++;if(entry.get("preloadFails").getAsBoolean())throw new IllegalStateException("authored-preload:"+(index+1));return null;
                }
                throw new IllegalStateException("Unselected weighted call:"+m.getName());
            });
            invoke(event,"event","add",new Class<?>[]{weighted},control);
        }
        Object realRandom=invoke(null,"random","create",new Class<?>[]{long.class},input.get("seed").getAsLong());
        Class<?> random=cls("random");Object recorder=Proxy.newProxyInstance(random.getClassLoader(),new Class<?>[]{random},(p,m,args)->{
            if(m.getDeclaringClass()==Object.class)return objectMethod(p,m,args);
            if(!m.getName().equals(name("random","nextInt")) || args==null || args.length!=1)throw new IllegalStateException("Unselected random call");
            JsonObject call=new JsonObject();call.addProperty("bound",(Integer)args[0]);call.add("draw",JsonNull.INSTANCE);call.addProperty("error","NONE");randomCalls.add(call);
            try {Integer draw=(Integer)invoke(realRandom,"random","nextInt",new Class<?>[]{int.class},args[0]);call.addProperty("draw",draw);return draw;}
            catch(ReflectiveOperationException e) {Throwable t=cause(e);call.addProperty("error",t.getClass().getName());throw t;}
        });
        String operation=input.get("operation").getAsString();Object result=null;String error="NONE",message="";boolean returned=false;JsonArray causes=new JsonArray();
        try {
            switch(operation) {
                case "weight" -> result=invoke(event,"event","weight",new Class<?>[]{});
                case "select" -> result=invoke(event,"event","select",new Class<?>[]{random},recorder);
                case "preload" -> invoke(event,"event","preload",new Class<?>[]{cls("engine")},new Object[]{null});
                default -> throw new IllegalArgumentException(operation);
            }
            returned=true;
        } catch(ReflectiveOperationException e) {
            Throwable t=cause(e);error=t.getClass().getName();message=String.valueOf(t.getMessage());
            for(int depth=0;t!=null && depth<8;depth++,t=t.getCause()) {
                JsonObject detail=new JsonObject();detail.addProperty("type",t.getClass().getName());detail.addProperty("message",String.valueOf(t.getMessage()));causes.add(detail);
            }
        }
        boolean fallback=false;
        if(returned && operation.equals("select") && selected[0]==0 && result!=null) {
            Field empty=cls("manager").getDeclaredField(bindings.getAsJsonObject("manager").getAsJsonObject("fields").get("EMPTY_SOUND").getAsString());empty.setAccessible(true);fallback=result==empty.get(null);
        }
        JsonObject row=new JsonObject();row.addProperty("case",input.get("id").getAsString());row.addProperty("operation",operation);
        row.addProperty("returned",returned);row.addProperty("returnedNull",result==null);row.addProperty("fallback",fallback);
        row.addProperty("selected",selected[0]);row.addProperty("error",error);row.addProperty("message",message);row.add("causes",causes);
        row.add("weight",returned && operation.equals("weight") ? new JsonPrimitive((Integer)result):JsonNull.INSTANCE);
        row.add("weightsRead",new Gson().toJsonTree(weightsRead));row.add("preloadCalls",new Gson().toJsonTree(preloads));row.add("reads",reads);row.add("random",randomCalls);
        boolean expected=error.equals("NONE") || (error.equals("java.lang.IllegalArgumentException") && randomCalls.size()==1 && randomCalls.get(0).getAsJsonObject().get("bound").getAsInt()<=0)
            || (error.equals("java.lang.IllegalStateException") && message.startsWith("authored-preload:"));
        row.addProperty("unexpected",!expected);return row;
    }
    public static void main(String[] args) throws Exception {
        bindings=JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();JsonObject request=JsonParser.parseString(Files.readString(Path.of(args[1]))).getAsJsonObject();JsonArray rows=new JsonArray();int errors=0;
        boolean prepared=bindings.getAsJsonObject("bootstrap").get("enabled").getAsBoolean();
        if(prepared) {invoke(null,"shared","detect",new Class<?>[]{});invoke(null,"bootstrap","prepare",new Class<?>[]{});}
        JsonArray decoded=new JsonArray();
        for(JsonElement element:request.getAsJsonArray("decoderCases")) {
            JsonObject input=element.getAsJsonObject(),row=new JsonObject();row.addProperty("case",input.get("id").getAsString());JsonArray weights=new JsonArray();
            try {
                Constructor<?> c=cls("serializer").getDeclaredConstructor();c.setAccessible(true);Object serializer=c.newInstance();
                Object registration=invoke(serializer,"serializer","decode",new Class<?>[]{JsonElement.class,java.lang.reflect.Type.class,JsonDeserializationContext.class},input.get("input"),cls("registration"),null);
                for(Object sound:(List<?>)invoke(registration,"registration","sounds",new Class<?>[]{}))weights.add((Integer)invoke(sound,"sound","weight",new Class<?>[]{}));
                row.addProperty("decoded",true);row.addProperty("error","NONE");
            } catch(ReflectiveOperationException e) {
                Throwable t=cause(e);row.addProperty("decoded",false);row.addProperty("error",t.getClass().getName());row.addProperty("message",String.valueOf(t.getMessage()));
                if(!(t instanceof IllegalArgumentException) && !(t instanceof JsonParseException))errors++;
            }
            row.add("weights",weights);decoded.add(row);
        }
        for(JsonElement element:request.getAsJsonArray("cases")) {JsonObject row=run(element.getAsJsonObject());rows.add(row);if(row.get("unexpected").getAsBoolean())errors++;}
        JsonObject output=new JsonObject();output.addProperty("schema",1);output.addProperty("observerErrors",errors);output.addProperty("bootstrapContext",prepared);output.add("decoderCases",decoded);output.add("cases",rows);
        Files.writeString(Path.of(args[2]),new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create().toJson(output)+"\n");
        System.out.println("Observed "+rows.size()+" original weighted cases;observerErrors="+errors+";no SoundEngine instance");
        System.exit(errors==0?0:2);
    }
}
