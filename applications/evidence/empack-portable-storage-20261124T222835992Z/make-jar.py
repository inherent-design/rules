import sys,zipfile
with zipfile.ZipFile(sys.argv[1],'w',compression=zipfile.ZIP_STORED) as z:
 z.writestr('META-INF/MANIFEST.MF','Manifest-Version: 1.0\n')
 z.writestr('study.txt','Opaque owned JAR fixture; no executable mod or game acceptance.\n')
