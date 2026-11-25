// Owner-run original 26.3 methods/codecs. No client/world/renderer startup.
package study.minecraft;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.serialization.Codec;
import com.mojang.serialization.DataResult;
import com.mojang.serialization.JsonOps;
import com.mojang.serialization.MapCodec;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import org.joml.Matrix4fc;
import org.joml.Vector3fc;

public final class LaterCodecProbe {
    private static final String PACK="net.minecraft.server.packs.metadata.pack.PackFormat";
    private static JsonObject format(Object value) throws ReflectiveOperationException {
        JsonObject out=new JsonObject();
        out.addProperty("major",(Integer)value.getClass().getMethod("major").invoke(value));
        out.addProperty("minor",(Integer)value.getClass().getMethod("minor").invoke(value));
        return out;
    }
    private static JsonArray vector(Vector3fc value) {
        JsonArray out=new JsonArray();out.add(value.x());out.add(value.y());out.add(value.z());return out;
    }
    private static JsonObject rotation(Object value) throws ReflectiveOperationException {
        JsonObject out=new JsonObject();
        if (value==null) {out.addProperty("kind","absent");return out;}
        Class<?> type=value.getClass();Object angles=type.getMethod("value").invoke(value);
        out.addProperty("kind",angles.getClass().getSimpleName());
        out.add("origin",vector((Vector3fc)type.getMethod("origin").invoke(value)));
        out.addProperty("rescale",(Boolean)type.getMethod("rescale").invoke(value));
        if (angles.getClass().getSimpleName().equals("EulerXYZRotation")) {
            JsonArray a=new JsonArray();for (String field:new String[]{"x","y","z"}) a.add((Float)angles.getClass().getMethod(field).invoke(angles));out.add("angles",a);
        } else {
            out.addProperty("axis",((Enum<?>)angles.getClass().getMethod("axis").invoke(angles)).name());
            out.addProperty("angle",(Float)angles.getClass().getMethod("angle").invoke(angles));
        }
        Matrix4fc matrix=(Matrix4fc)type.getMethod("transform").invoke(value);JsonArray m=new JsonArray();
        // Explicit JOML component order,not an inferred renderer convention.
        for (float f:new float[]{matrix.m00(),matrix.m01(),matrix.m02(),matrix.m03(),matrix.m10(),matrix.m11(),matrix.m12(),matrix.m13(),matrix.m20(),matrix.m21(),matrix.m22(),matrix.m23(),matrix.m30(),matrix.m31(),matrix.m32(),matrix.m33()}) m.add(f);
        out.add("jomlComponents_m00_m01_m02_m03_m10_through_m33",m);return out;
    }
    private static Object decoder() throws ReflectiveOperationException {
        Class<?> type=Class.forName("net.minecraft.client.resources.model.cuboid.CuboidModelElement$Deserializer");
        Constructor<?> constructor=type.getDeclaredConstructor();constructor.setAccessible(true);return constructor.newInstance();
    }
    private static JsonObject evaluate(JsonObject request) throws ReflectiveOperationException {
        String action=request.get("action").getAsString();JsonElement input=request.get("input");JsonObject result=new JsonObject();
        if (action.equals("rotation") || action.equals("shade")) {
            Object parser=decoder();Method method=parser.getClass().getDeclaredMethod(action.equals("rotation")?"getRotation":"getShadeDirectionOverride",JsonObject.class);method.setAccessible(true);
            Object value=method.invoke(parser,input.getAsJsonObject());result.addProperty("accepted",true);
            if (action.equals("rotation")) result.add("value",rotation(value));
            else result.add("value",value==null?JsonNull.INSTANCE:new com.google.gson.JsonPrimitive(((Enum<?>)value).name()));
            return result;
        }
        Codec<?> codec;
        Class<?> pack=Class.forName(PACK);
        if (action.equals("format-bottom") || action.equals("format-top")) {
            codec=(Codec<?>)pack.getField(action.equals("format-bottom")?"BOTTOM_CODEC":"TOP_CODEC").get(null);
        } else if (action.equals("pack-resource") || action.equals("pack-data")) {
            Class<?> packType=Class.forName("net.minecraft.server.packs.PackType");String name=action.equals("pack-resource")?"CLIENT_RESOURCES":"SERVER_DATA";Object selected=null;
            for (Object candidate:packType.getEnumConstants()) if (((Enum<?>)candidate).name().equals(name)) selected=candidate;
            if (selected==null) throw new IllegalArgumentException("Unknown original pack type");
            codec=((MapCodec<?>)pack.getMethod("packCodec",packType).invoke(null,selected)).codec();
        } else throw new IllegalArgumentException("Unsupported observer action");
        DataResult<?> decoded=codec.parse(JsonOps.INSTANCE,input);result.addProperty("accepted",decoded.result().isPresent());
        if (decoded.result().isEmpty()) {result.addProperty("error",decoded.error().orElseThrow().message());return result;}
        Object value=decoded.result().orElseThrow();
        if (action.startsWith("format-")) result.add("value",format(value));
        else {
            JsonObject range=new JsonObject();range.add("min",format(value.getClass().getMethod("minInclusive").invoke(value)));range.add("max",format(value.getClass().getMethod("maxInclusive").invoke(value)));result.add("value",range);
        }
        return result;
    }
    public static void main(String[] args) throws Exception {
        if (args.length!=2) throw new IllegalArgumentException("Supply frozen request and output paths");
        JsonObject request=JsonParser.parseString(Files.readString(Path.of(args[0]),StandardCharsets.UTF_8)).getAsJsonObject();
        if (request.get("schema").getAsInt()!=1) throw new IllegalArgumentException("Unsupported request schema");
        JsonArray results=new JsonArray();int errors=0;
        for (JsonElement element:request.getAsJsonArray("cases")) {
            JsonObject row=element.getAsJsonObject();JsonObject out=new JsonObject();out.addProperty("case",row.get("id").getAsString());out.addProperty("action",row.get("action").getAsString());out.add("input",row.get("input").deepCopy());
            try {out.add("observed",evaluate(row));}
            catch (InvocationTargetException failure) {
                Throwable cause=failure.getCause();boolean refusal=cause instanceof com.google.gson.JsonParseException || cause instanceof IllegalArgumentException;
                JsonObject state=new JsonObject();state.addProperty("accepted",false);state.addProperty("exception",cause.getClass().getName());state.addProperty("message",cause.getMessage());out.add("observed",state);
                if (!refusal) {out.addProperty("observerError",true);errors++;}
            } catch (ReflectiveOperationException|LinkageError|RuntimeException failure) {
                out.addProperty("observerError",true);out.addProperty("exception",failure.getClass().getName());out.addProperty("message",failure.getMessage());errors++;
            }
            results.add(out);
        }
        JsonObject output=new JsonObject();output.addProperty("schema",1);output.addProperty("observerErrors",errors);output.add("cases",results);
        Files.writeString(Path.of(args[1]),output.toString()+"\n",StandardCharsets.UTF_8);System.out.println("cases="+results.size()+" observerErrors="+errors);
        if (errors!=0) System.exit(3);
    }
}
