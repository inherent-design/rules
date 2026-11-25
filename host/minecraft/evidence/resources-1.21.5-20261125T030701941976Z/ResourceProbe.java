// Owner-run original-client resource-manager observer; generated private folders only.
package study.minecraft;

import com.google.gson.*;
import java.io.InputStream;
import java.lang.reflect.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.function.Predicate;

public final class ResourceProbe {
    private static JsonObject bindings;
    private static Class<?> type(String name) throws ClassNotFoundException {
        return Class.forName(bindings.getAsJsonObject(name).get("name").getAsString());
    }
    private static Object field(String owner, String name, Object receiver) throws ReflectiveOperationException {
        String locator = bindings.getAsJsonObject(owner).getAsJsonObject("fields").get(name).getAsString();
        Field selected = type(owner).getDeclaredField(locator);
        selected.setAccessible(true);
        return selected.get(receiver);
    }
    private static Object call(String owner, String signature, Object receiver, Class<?>[] params, Object... args) throws ReflectiveOperationException {
        JsonElement locator = bindings.getAsJsonObject(owner).getAsJsonObject("methods").get(signature);
        if (locator == null) throw new NoSuchMethodException(owner+"."+signature);
        Method selected = type(owner).getDeclaredMethod(locator.getAsString(),params);
        selected.setAccessible(true);
        return selected.invoke(receiver,args);
    }
    private static Object create(String owner, Class<?>[] params, Object... args) throws ReflectiveOperationException {
        Constructor<?> selected = type(owner).getDeclaredConstructor(params);
        selected.setAccessible(true);
        return selected.newInstance(args);
    }
    private static Throwable unwrap(Throwable e) {
        while (e instanceof InvocationTargetException && e.getCause()!=null) e=e.getCause();
        return e;
    }
    private static JsonObject error(Throwable original) {
        Throwable e=unwrap(original);
        JsonObject result=new JsonObject();
        result.addProperty("exception",e.getClass().getName());
        result.addProperty("message",String.valueOf(e.getMessage()));
        result.addProperty("observerError",e instanceof ReflectiveOperationException || e instanceof LinkageError);
        return result;
    }
    private static JsonObject resource(Object resource, boolean successor) throws Exception {
        String owner="net.minecraft.server.packs.resources.Resource";
        JsonObject result=new JsonObject();
        result.addProperty("source",(String)call(owner,"sourcePackId()",resource,new Class<?>[0]));
        try (InputStream stream=(InputStream)call(owner,"open()",resource,new Class<?>[0])) {
            result.addProperty("content",new String(stream.readAllBytes(),StandardCharsets.UTF_8));
        }
        try {
            Object metadata=call(owner,"metadata()",resource,new Class<?>[0]);
            String holder="net.minecraft.client.resources.metadata.texture.TextureMetadataSection";
            String parameter=successor?"net.minecraft.server.packs.metadata.MetadataSectionType":"net.minecraft.server.packs.metadata.MetadataSectionSerializer";
            Object serializer=field(holder,successor?"TYPE":"SERIALIZER",null);
            Optional<?> section=(Optional<?>)call("net.minecraft.server.packs.resources.ResourceMetadata","getSection("+parameter+")",metadata,new Class<?>[]{type(parameter)},serializer);
            result.addProperty("textureMetadata",section.isPresent());
            if (section.isPresent()) {
                result.addProperty("blur",(Boolean)field(holder,"blur",section.get()));
                result.addProperty("clamp",(Boolean)field(holder,"clamp",section.get()));
            }
        } catch (Throwable e) {
            result.add("metadataError",error(e));
        }
        return result;
    }
    private static JsonObject observe(JsonObject row, boolean successor, Path root) throws Exception {
        String pack="net.minecraft.server.packs.PathPackResources";
        String info="net.minecraft.server.packs.PackLocationInfo";
        String component="net.minecraft.network.chat.Component";
        String source="net.minecraft.server.packs.repository.PackSource";
        String packType="net.minecraft.server.packs.PackType";
        String manager="net.minecraft.server.packs.resources.MultiPackResourceManager";
        String id="net.minecraft.resources.ResourceLocation";
        List<Object> packs=new ArrayList<>();
        for (JsonElement item:row.getAsJsonArray("order")) {
            String name=item.getAsString();
            Object title=call(component,"literal(java.lang.String)",null,new Class<?>[]{String.class},name);
            Object location=create(info,new Class<?>[]{String.class,type(component),type(source),Optional.class},name,title,field(source,"DEFAULT",null),Optional.empty());
            packs.add(create(pack,new Class<?>[]{type(info),Path.class},location,root.resolve(name)));
        }
        Object rm=create(manager,new Class<?>[]{type(packType),List.class},field(packType,"CLIENT_RESOURCES",null),packs);
        JsonObject result=new JsonObject();result.addProperty("id",row.get("id").getAsString());
        try {
            Object location=call(id,"parse(java.lang.String)",null,new Class<?>[]{String.class},row.get("query").getAsString());
            Optional<?> single=(Optional<?>)call(manager,"getResource(net.minecraft.resources.ResourceLocation)",rm,new Class<?>[]{type(id)},location);
            result.add("single",single.isPresent()?resource(single.get(),successor):JsonNull.INSTANCE);
            JsonArray stack=new JsonArray();
            for (Object r:(List<?>)call(manager,"getResourceStack(net.minecraft.resources.ResourceLocation)",rm,new Class<?>[]{type(id)},location)) stack.add(resource(r,successor));
            result.add("stack",stack);
            try {
                Map<?,?> listed=(Map<?,?>)call(manager,"listResources(java.lang.String,java.util.function.Predicate)",rm,new Class<?>[]{String.class,Predicate.class},row.get("prefix").getAsString(),(Predicate<Object>)x->true);
                JsonArray entries=new JsonArray();
                for (Map.Entry<?,?> e:listed.entrySet()) {
                    JsonObject entry=resource(e.getValue(),successor);
                    entry.addProperty("location",e.getKey().toString());entries.add(entry);
                }
                result.add("listed",entries);
            } catch (Throwable e) {result.add("listError",error(e));}
        } catch (Throwable e) {result.add("error",error(e));}
        finally {call(manager,"close()",rm,new Class<?>[0]);}
        return result;
    }
    public static void main(String[] args) throws Exception {
        if(args.length!=2) throw new IllegalArgumentException("Supply request and result paths.");
        JsonObject request=JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();
        bindings=request.getAsJsonObject("mappings");
        call("net.minecraft.SharedConstants","tryDetectVersion()",null,new Class<?>[0]);
        call("net.minecraft.server.Bootstrap","bootStrap()",null,new Class<?>[0]);
        JsonArray results=new JsonArray();
        for(JsonElement item:request.getAsJsonArray("cases")) results.add(observe(item.getAsJsonObject(),request.get("successor").getAsBoolean(),Path.of(request.get("fixtureRoot").getAsString())));
        Files.writeString(Path.of(args[1]),new GsonBuilder().serializeNulls().setPrettyPrinting().create().toJson(results)+"\n");
    }
}
