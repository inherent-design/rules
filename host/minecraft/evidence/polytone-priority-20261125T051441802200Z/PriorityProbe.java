// Execute one unchanged original policy class with explicitly substituted data/log adapters.
package study.mc;
import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import net.mehvahdjukaar.polytone.Polytone;
import net.mehvahdjukaar.polytone.common.Parsed;
import net.minecraft.resources.ResourceLocation;

public final class PriorityProbe {
    private record Action(int key,boolean enabled,int priority,int marker) {
        String json() { return "{\"key\":"+key+",\"enabled\":"+enabled+",\"priority\":"+priority+",\"marker\":"+marker+"}"; }
    }
    private static final List<String> results=new ArrayList<>();
    private static Constructor<?> constructor;
    private static Method put,size,keySet,values,entrySet,get;
    private static String entries(Iterable<?> entries) {
        List<String> result=new ArrayList<>();
        for (Object item:entries) {
            if (!(item instanceof Map.Entry<?,?> entry) || !(entry.getKey() instanceof ResourceLocation key) || !(entry.getValue() instanceof Parsed<?> value)) throw new IllegalStateException("Unsupported original result shape");
            result.add("{\"key\":"+key.key()+",\"enabled\":"+value.enabled+",\"priority\":"+value.priority+",\"marker\":"+value.marker+"}");
        }
        return "["+String.join(",",result)+"]";
    }
    private static void run(String name,List<Action> actions) throws Exception {
        Object map=constructor.newInstance("private-fixture");Polytone.warnings=0;
        for (Action a:actions) put.invoke(map,new ResourceLocation(a.key()),new Parsed<>(a.enabled(),a.priority(),a.marker()));
        List<String> keys=new ArrayList<>(),markers=new ArrayList<>(),raw=new ArrayList<>();
        for (Object key:(Collection<?>)keySet.invoke(map)) keys.add(Integer.toString(((ResourceLocation)key).key()));
        for (Object value:(Collection<?>)values.invoke(map)) markers.add(((Parsed<?>)value).marker.toString());
        for (Action a:actions) raw.add(a.json());
        Object selected=get.invoke(map,new ResourceLocation(0));
        String marker=selected==null?"null":((Parsed<?>)selected).marker.toString();
        results.add("{\"case\":\""+name+"\",\"actions\":["+String.join(",",raw)+"],\"observed\":{\"size\":"+size.invoke(map)+",\"warnings\":"+Polytone.warnings+",\"selectedZeroMarker\":"+marker+",\"insertionKeys\":["+String.join(",",keys)+"],\"insertionMarkers\":["+String.join(",",markers)+"],\"iterator\":"+entries((Iterable<?>)map)+",\"entrySet\":"+entries((Iterable<?>)entrySet.invoke(map))+"}}");
    }
    public static void main(String[] args) throws Exception {
        if (args.length!=0) throw new IllegalArgumentException("No external input accepted");
        Class<?> type=Class.forName("net.mehvahdjukaar.polytone.common.Parsed$SortedMap");
        String originalHash;
        try (var in=type.getResourceAsStream("Parsed$SortedMap.class")) {
            if (in==null) throw new IllegalStateException("Original class bytes unavailable");
            originalHash=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(in.readAllBytes()));
        }
        constructor=type.getConstructor(String.class);put=type.getMethod("put",ResourceLocation.class,Parsed.class);size=type.getMethod("size");keySet=type.getMethod("keySet");values=type.getMethod("values");entrySet=type.getMethod("entrySet");get=type.getMethod("get",ResourceLocation.class);
        for (boolean enabled:List.of(false,true)) for (int priority:List.of(-1,0,1)) run("empty-"+enabled+"-"+priority,List.of(new Action(0,enabled,priority,2)));
        for (boolean oldEnabled:List.of(false,true)) for (int oldPriority:List.of(-1,0,1)) for (boolean enabled:List.of(false,true)) for (int priority:List.of(-1,0,1)) run("pair-"+oldEnabled+"-"+oldPriority+"-"+enabled+"-"+priority,List.of(new Action(0,oldEnabled,oldPriority,1),new Action(0,enabled,priority,2)));
        run("tie-forward",List.of(new Action(0,true,0,1),new Action(1,true,0,2)));
        run("tie-reverse",List.of(new Action(1,true,0,2),new Action(0,true,0,1)));
        run("priority-vs-insertion",List.of(new Action(0,true,1,1),new Action(1,true,-1,2)));
        run("replacement-keeps-position",List.of(new Action(0,true,-1,1),new Action(1,true,1,2),new Action(0,true,1,3)));
        run("equal-does-not-replace",List.of(new Action(0,true,0,1),new Action(1,true,0,2),new Action(0,true,0,3)));
        run("disabled-high-stays",List.of(new Action(0,false,1,1),new Action(1,true,0,2),new Action(0,true,0,3)));
        System.out.println("{\"schema\":1,\"originalClassSha256\":\""+originalHash+"\",\"cases\":["+String.join(",",results)+"]}");
    }
}
