package study.minecraft;

import com.google.gson.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

/** Original reload orchestration with authored listeners,gates and direct executors. */
public final class ReloadProbe {
    private ReloadProbe() { }
    private static final class FixtureFailure extends RuntimeException {
        private static final long serialVersionUID=1L;
        FixtureFailure(String reason) {super(reason);}
    }
    private static int observerErrors;
    private static final Gson gson=new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();
    private static Throwable cause(Throwable error) {
        while((error instanceof InvocationTargetException||error instanceof CompletionException)&&error.getCause()!=null)error=error.getCause();
        return error;
    }
    private static int state(CompletableFuture<?> future) {
        return future==null?3:!future.isDone()?0:future.isCompletedExceptionally()?2:1;
    }
    private static Object objectMethod(Object proxy,Method method,Object[] args) {
        return switch(method.getName()) {
            case "hashCode"->System.identityHashCode(proxy);
            case "equals"->proxy==args[0];
            case "toString"->"authored-reload-listener";
            default->throw new UnsupportedOperationException(method.toString());
        };
    }
    private static final class Study {
        final List<Integer> effects=new ArrayList<>(),invoked=new ArrayList<>(),shared=new ArrayList<>(),barriers=new ArrayList<>();
        final List<String> events=new ArrayList<>();
        final List<CompletableFuture<Void>> preparations=new ArrayList<>(),children=new ArrayList<>();
        final CompletableFuture<Void> initial=new CompletableFuture<>();
        final JsonArray snapshots=new JsonArray();
        final JsonObject spec,binding;
        final boolean hasShared;
        Object firstShared;
        boolean sameShared=true;
        CompletableFuture<?> done;
        String factory="not-called";
        Study(JsonObject spec,JsonObject binding,boolean hasShared) {
            this.spec=spec;this.binding=binding;this.hasShared=hasShared;
        }
        void snapshot(String phase) {
            JsonObject row=new JsonObject();row.addProperty("phase",phase);row.addProperty("factory",factory);
            row.addProperty("initial",state(initial));row.addProperty("overall",state(done));
            row.add("preparations",gson.toJsonTree(preparations.stream().map(ReloadProbe::state).toList()));
            row.add("listenerFutures",gson.toJsonTree(children.stream().map(ReloadProbe::state).toList()));
            row.add("effects",gson.toJsonTree(effects));row.add("invoked",gson.toJsonTree(invoked));
            row.add("shared",gson.toJsonTree(shared));row.add("barriers",gson.toJsonTree(barriers));
            row.add("events",gson.toJsonTree(events));row.addProperty("sameSharedContext",sameShared);
            snapshots.add(row);
        }
        @SuppressWarnings("unchecked")
        void execute() throws Exception {
            Class<?> simple=Class.forName(binding.getAsJsonObject("simple").get("class").getAsString());
            Class<?> manager=Class.forName(binding.getAsJsonObject("manager").get("class").getAsString());
            Class<?> listener=Class.forName(binding.getAsJsonObject("listener").get("class").getAsString());
            Class<?> barrier=Class.forName(binding.getAsJsonObject("barrier").get("class").getAsString());
            Class<?> instance=Class.forName(binding.getAsJsonObject("instance").get("class").getAsString());
            JsonObject methods=binding.getAsJsonObject("listener").getAsJsonObject("methods");
            Method wait=barrier.getDeclaredMethod(binding.getAsJsonObject("barrier").getAsJsonObject("methods").get("wait").getAsString(),Object.class);
            wait.setAccessible(true);
            Object resource=Proxy.newProxyInstance(manager.getClassLoader(),new Class<?>[]{manager},(p,m,a)->{
                if(m.getDeclaringClass()==Object.class)return objectMethod(p,m,a);
                throw new UnsupportedOperationException("ResourceManager methods are outside the fixture.");
            });
            List<Object> listeners=new ArrayList<>();int count=spec.get("count").getAsInt();
            for(int i=0;i<count;i++) {
                preparations.add(new CompletableFuture<>());children.add(null);final int id=i;
                listeners.add(Proxy.newProxyInstance(listener.getClassLoader(),new Class<?>[]{listener},(p,m,a)->{
                    if(m.getDeclaringClass()==Object.class)return objectMethod(p,m,a);
                    if(hasShared&&m.getName().equals(methods.get("prepareSharedState").getAsString())&&m.getParameterCount()==1) {
                        shared.add(id);events.add("shared"+id);
                        if(firstShared==null)firstShared=a[0];else sameShared&=firstShared==a[0];
                        if(spec.get("sharedFails").getAsInt()==id)throw new FixtureFailure("shared"+id);
                        return null;
                    }
                    if(m.getName().equals(methods.get("reload").getAsString())&&CompletableFuture.class.isAssignableFrom(m.getReturnType())) {
                        invoked.add(id);events.add("invoke"+id);
                        Object gate=Arrays.stream(a).filter(barrier::isInstance).findFirst().orElseThrow();
                        Executor applyExecutor=(Executor)a[a.length-1];
                        CompletableFuture<Void> child=preparations.get(id).thenCompose(value->{
                            boolean useBarrier=id!=0||spec.get("barrier0").getAsBoolean();
                            if(!useBarrier)return CompletableFuture.completedFuture(null);
                            barriers.add(id);events.add("barrier"+id);
                            try{return (CompletableFuture<Void>)wait.invoke(gate,(Object)null);}
                            catch(ReflectiveOperationException error){return CompletableFuture.failedFuture(cause(error));}
                        }).thenRunAsync(()->{
                            effects.add(id);events.add("effect"+id);
                            if(id==0&&spec.get("applyFails0").getAsBoolean())throw new FixtureFailure("apply0");
                        },applyExecutor);
                        children.set(id,child);return child;
                    }
                    if(m.getReturnType()==String.class&&m.getParameterCount()==0)return "fixture-"+id;
                    throw new UnsupportedOperationException("Unselected listener method: "+m);
                }));
            }
            int initialStatus=spec.get("initial").getAsInt();
            if(initialStatus==1)initial.complete(null);
            else if(initialStatus==2)initial.completeExceptionally(new FixtureFailure("initial"));
            Method create=simple.getDeclaredMethod(binding.getAsJsonObject("simple").getAsJsonObject("methods").get("create").getAsString(),manager,List.class,Executor.class,Executor.class,CompletableFuture.class,boolean.class);
            Method complete=instance.getDeclaredMethod(binding.getAsJsonObject("instance").getAsJsonObject("methods").get("done").getAsString());
            create.setAccessible(true);complete.setAccessible(true);Executor direct=Runnable::run;
            try {
                Object reload=create.invoke(null,resource,listeners,direct,direct,initial,false);
                done=(CompletableFuture<?>)complete.invoke(reload);factory="returned";
            } catch(InvocationTargetException error) {
                Throwable actual=cause(error);factory="threw-"+actual.getClass().getSimpleName();
                if(!(actual instanceof FixtureFailure))observerErrors++;
            }
            snapshot("created");
            for(JsonElement item:spec.getAsJsonArray("actions")) {
                JsonObject action=item.getAsJsonObject();int target=action.get("target").getAsInt(),value=action.get("value").getAsInt();
                CompletableFuture<Void> selected=target<0?initial:preparations.get(target);
                boolean changed=value==1?selected.complete(null):selected.completeExceptionally(new FixtureFailure("prepare"+target));
                if(!changed)throw new IllegalStateException("Repeated completion outside authored plan.");
                snapshot("complete-"+target+"-"+value);
            }
        }
    }
    public static void main(String[] args) throws Exception {
        if(args.length!=3)throw new IllegalArgumentException("Supply bindings,request and output.");
        JsonObject binding=JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();
        JsonObject request=JsonParser.parseString(Files.readString(Path.of(args[1]))).getAsJsonObject();
        if(request.get("schema").getAsInt()!=1)throw new IllegalArgumentException("Unselected research schema.");
        boolean hasShared=request.get("hasSharedState").getAsBoolean();JsonArray cases=new JsonArray();
        for(JsonElement item:request.getAsJsonArray("cases")) {
            JsonObject spec=item.getAsJsonObject(),out=new JsonObject();out.addProperty("id",spec.get("id").getAsString());
            if(spec.get("requiresSharedState").getAsBoolean()&&!hasShared) {
                out.addProperty("skipped","selected listener interface lacks this hook");cases.add(out);continue;
            }
            Study study=new Study(spec,binding,hasShared);study.execute();out.add("snapshots",study.snapshots);cases.add(out);
        }
        JsonObject output=new JsonObject();output.addProperty("schema",1);output.addProperty("observerErrors",observerErrors);output.add("cases",cases);
        Files.writeString(Path.of(args[2]),gson.toJson(output)+"\n");System.out.println("Recorded "+cases.size()+" reload research cases;authored listeners/direct executors,no game.");
    }
}
