package study.minecraft;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.serialization.Codec;
import com.mojang.serialization.JsonOps;
import java.util.Optional;
import net.mehvahdjukaar.codecui.Schema;
import net.mehvahdjukaar.codecui.SchemaCodec;
import net.mehvahdjukaar.codecui.SchemaRecord;

/** Authored one-field callers of unchanged bundled CodecUI classes. No game adapter. */
public final class SchemaRecordProbe {
    private record Box(Integer value) {}
    private record OptBox(Optional<Integer> value) {}

    private static SchemaCodec<?> codec(String form) {
        SchemaCodec<Integer> integer = SchemaCodec.of(Codec.INT, new Schema.IntRange(Integer.MIN_VALUE, Integer.MAX_VALUE));
        return switch (form) {
            case "required" -> SchemaRecord.create(Box.class, i -> i.group(i.field("value", integer, Box::value)).apply(i, Box::new));
            case "optional-wrapper" -> SchemaRecord.create(OptBox.class, i -> i.group(i.optional("value", integer, OptBox::value)).apply(i, OptBox::new));
            case "default-zero" -> SchemaRecord.create(Box.class, i -> i.group(i.optional("value", integer, 0, Box::value)).apply(i, Box::new));
            case "default-null" -> SchemaRecord.create(Box.class, i -> i.group(i.optional("value", integer, (Integer) null, Box::value)).apply(i, Box::new));
            case "map-required" -> SchemaRecord.create(Box.class, i -> i.group(i.field("value", Codec.INT.fieldOf("value"), integer, Box::value)).apply(i, Box::new));
            case "map-default-two" -> SchemaRecord.create(Box.class, i -> i.group(i.field("value", Codec.INT.optionalFieldOf("value", 2), integer, Box::value)).apply(i, Box::new));
            default -> throw new IllegalArgumentException(form);
        };
    }

    private static <A> JsonObject observe(String form, String inputKind, JsonElement input, SchemaCodec<A> codec) {
        JsonObject row = new JsonObject();
        row.addProperty("form", form);
        row.addProperty("inputKind", inputKind);
        row.add("input", input);
        Schema.Record<?> schema = (Schema.Record<?>) codec.schema();
        Schema.Field<?, ?> field = schema.fields().getFirst();
        row.addProperty("advertisedOptional", field.optional());
        row.addProperty("advertisedInline", field.inline());
        row.addProperty("advertisedName", field.name());
        if (field.defaultValue() == null) row.add("advertisedDefault", null);
        else row.addProperty("advertisedDefault", (Integer) field.defaultValue());
        var result = codec.parse(JsonOps.INSTANCE, input);
        row.addProperty("success", result.isSuccess());
        if (result.isSuccess()) {
            A decoded = result.getOrThrow();
            Integer value = decoded instanceof Box box ? box.value() : ((OptBox) decoded).value().orElse(null);
            row.addProperty("valuePresent", value != null);
            if (value == null) row.add("value", null); else row.addProperty("value", value);
            var encoded = codec.encodeStart(JsonOps.INSTANCE, decoded);
            row.addProperty("encodeSuccess", encoded.isSuccess());
            if (encoded.isSuccess()) row.add("encoded", encoded.getOrThrow());
            else row.addProperty("encodeError", encoded.error().orElseThrow().message());
        } else row.addProperty("error", result.error().orElseThrow().message());
        return row;
    }

    public static void main(String[] args) {
        JsonArray cases = new JsonArray();
        String[] forms = {"required", "optional-wrapper", "default-zero", "default-null", "map-required", "map-default-two"};
        String[] kinds = {"missing", "zero", "seven", "wrong-type", "null"};
        String[] inputs = {"{}", "{\"value\":0}", "{\"value\":7}", "{\"value\":\"bad\"}", "{\"value\":null}"};
        for (String form : forms) {
            SchemaCodec<?> codec = codec(form);
            for (int i = 0; i < kinds.length; i++) cases.add(observe(form, kinds[i], JsonParser.parseString(inputs[i]), codec));
        }
        JsonObject result = new JsonObject();
        result.addProperty("schema", 1);
        result.add("cases", cases);
        System.out.println(result);
    }
}
