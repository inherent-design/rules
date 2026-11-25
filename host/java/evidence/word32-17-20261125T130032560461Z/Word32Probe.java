package study.host;

/** Authored runtime int operations; no application classes or external libraries. */
public final class Word32Probe {
    private Word32Probe() { }
    public static void main(String[] args) {
        int[][] pairs={{2147483647,1},{2147483647,2147483647},{0,1},{-2147483648,1},
            {0,-2147483648},{1073741824,1073741824},{-1,-1},{1,2},{-2,4},{-2147483648,2147483647}};
        StringBuilder out=new StringBuilder("{\"schema\":1,\"rows\":[");
        for(int i=0;i<pairs.length;i++) {
            if(i!=0)out.append(',');int a=pairs[i][0],b=pairs[i][1],add=a+b,sub=a-b;
            out.append("{\"index\":").append(i).append(",\"a\":").append(a).append(",\"b\":").append(b)
                .append(",\"sum\":").append(add).append(",\"difference\":").append(sub)
                .append(",\"sumBits\":").append(Integer.toUnsignedLong(add)).append(",\"differenceBits\":").append(Integer.toUnsignedLong(sub))
                .append(",\"negative\":").append(add<0).append(",\"positive\":").append(add>0).append('}');
        }
        System.out.println(out.append("]}"));
    }
}
