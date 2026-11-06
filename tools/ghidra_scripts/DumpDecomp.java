// Dump every function of the current program as decompiled C.
// Usage (headless):
//   analyzeHeadless <projDir> <projName> -import <binary> \
//     -scriptPath tools/ghidra_scripts -postScript DumpDecomp.java <outDir> [-noanalysis]
//@category Publisher
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;

import java.io.File;
import java.io.PrintWriter;

public class DumpDecomp extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String outDir = args.length > 0 ? args[0] : "decomp";
        File dir = new File(outDir);
        if (!dir.exists() && !dir.mkdirs()) {
            throw new RuntimeException("cannot create " + outDir);
        }
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        ifc.setSimplificationStyle("decompile");

        PrintWriter index = new PrintWriter(new File(dir, "_index.tsv"), "UTF-8");
        index.println("entry\tname\tsize\tdecompiled");
        FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
        int n = 0, ok = 0;
        while (it.hasNext() && !monitor.isCancelled()) {
            Function f = it.next();
            String name = f.getName();
            String safe = name.replaceAll("[^A-Za-z0-9_.@$?-]", "_");
            DecompileResults res = ifc.decompileFunction(f, 60, monitor);
            boolean good = res != null && res.decompileCompleted() && res.getDecompiledFunction() != null;
            PrintWriter w = new PrintWriter(new File(dir, String.format("%08x_%s.c",
                    f.getEntryPoint().getOffset(), safe)), "UTF-8");
            w.println("// " + name + " @ " + f.getEntryPoint());
            w.println("// signature: " + f.getPrototypeString(false, false));
            if (good) {
                w.println(res.getDecompiledFunction().getC());
                ok++;
            } else {
                w.println("// DECOMPILE FAILED: " + (res == null ? "null" : res.getErrorMessage()));
            }
            w.close();
            index.println(f.getEntryPoint() + "\t" + name + "\t" + f.getBody().getNumAddresses() + "\t" + good);
            n++;
            if ((n % 200) == 0) {
                println("decompiled " + n);
            }
        }
        index.close();
        println("DONE functions=" + n + " decompiled=" + ok + " out=" + dir.getAbsolutePath());
    }
}
