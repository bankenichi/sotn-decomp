/* Ghidra postScript for the SOTN stub evidence pilot.
 *
 * Runs AFTER auto-analysis. For every target address it decompiles the
 * function and writes <outDir>/<name>.c, plus one summary.json carrying the
 * callee and caller lists Ghidra derived for each target.
 *
 * Args: <outDir> <targetFile>
 */

import java.io.File;
import java.io.FileWriter;
import java.io.BufferedReader;
import java.io.FileReader;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.util.task.TaskMonitor;

public class SotnExportPostScript extends GhidraScript {

	private static final Pattern TARGET = Pattern
			.compile("^(0x[0-9A-Fa-f]+)\\s+([A-Za-z_][A-Za-z0-9_]*)");

	private static String jstr(String s) {
		if (s == null) {
			return "\"\"";
		}
		StringBuilder b = new StringBuilder("\"");
		for (int i = 0; i < s.length(); i++) {
			char c = s.charAt(i);
			if (c == '"' || c == '\\') {
				b.append('\\');
				b.append(c);
			} else if (c == '\r') {
				// skip
			} else if (c == '\n') {
				b.append("\\n");
			} else {
				b.append(c);
			}
		}
		return b.append('"').toString();
	}

	@Override
	public void run() throws Exception {
		String[] args = getScriptArgs();
		if (args.length < 2) {
			throw new IllegalArgumentException(
					"usage: SotnExportPostScript.java <outDir> <targetFile>");
		}
		String outDir = args[0];
		String targetFile = args[1];
		File out = new File(outDir);
		out.mkdirs();

		// parse targets
		List<long[]> addrs = new ArrayList<long[]>();
		List<String> names = new ArrayList<String>();
		BufferedReader tin = new BufferedReader(new FileReader(targetFile));
		try {
			String line;
			while ((line = tin.readLine()) != null) {
				Matcher m = TARGET.matcher(line.trim());
				if (!m.find()) {
					continue;
				}
				addrs.add(new long[] { Long.parseLong(m.group(1).substring(2), 16) });
				names.add(m.group(2));
			}
		} finally {
			tin.close();
		}

		DecompInterface decomp = new DecompInterface();
		decomp.setOptions(new DecompileOptions());
		decomp.openProgram(currentProgram);

		StringBuilder summary = new StringBuilder();
		int ok = 0;
		int fail = 0;
		for (int i = 0; i < addrs.size(); i++) {
			long addrVal = addrs.get(i)[0];
			String name = names.get(i);
			Address a = toAddr(addrVal);
			Function f = getFunctionAt(a);
			if (f == null) {
				f = createFunction(a, name);
			}
			List<String> callees = new ArrayList<String>();
			List<String> callers = new ArrayList<String>();
			try {
				for (Function cf : f.getCalledFunctions(monitor)) {
					callees.add(cf.getName());
				}
			} catch (Throwable t) {
				try {
					for (Function cf : f.getCalledFunctions(TaskMonitor.DUMMY)) {
						callees.add(cf.getName());
					}
				} catch (Throwable t2) {
					// callee API unavailable; the C body still carries call sites
				}
			}
			try {
				for (Function cf : f.getCallingFunctions(monitor)) {
					callers.add(cf.getName());
				}
			} catch (Throwable t) {
				try {
					for (Function cf : f.getCallingFunctions(TaskMonitor.DUMMY)) {
						callers.add(cf.getName());
					}
				} catch (Throwable t2) {
					// caller API unavailable
				}
			}

			DecompileResults res = null;
			String c = null;
			String error = "";
			if (f != null) {
				res = decomp.decompileFunction(f, 240, monitor);
				if (res != null && res.decompileCompleted()) {
					c = res.getDecompiledFunction().getC();
				} else {
					error = res == null ? "null result" : res.getErrorMessage();
				}
			} else {
				error = "function could not be created at 0x" + Long.toHexString(addrVal);
			}

			if (c != null) {
				String safe = name.replaceAll("[^A-Za-z0-9_.-]", "_");
				PrintWriter pw = new PrintWriter(new FileWriter(new File(out, safe + ".c"), false));
				try {
					// keep provenance: the target is the retail overlay listing
					pw.print("// decompiled by Ghidra headless (SOTN stub evidence pilot)\n");
					pw.print("// addr 0x" + Long.toHexString(addrVal) + " name " + name + "\n\n");
					pw.print(c);
				} finally {
					pw.close();
				}
				ok++;
			} else {
				fail++;
			}

			Set<String> uniqCallees = new LinkedHashSet<String>(callees);
			Set<String> uniqCallers = new LinkedHashSet<String>(callers);
			if (summary.length() > 0) {
				summary.append(",\n  ");
			}
			summary.append("{\"name\": " + jstr(name));
			summary.append(", \"addr\": " + jstr("0x" + Long.toHexString(addrVal)));
			summary.append(", \"status\": " + jstr(c != null ? "ok" : "error"));
			if (f != null) {
				summary.append(", \"body_bytes\": "
						+ Long.valueOf(f.getBody().getNumAddresses()));
			}
			summary.append(", \"callees\": [");
			boolean first = true;
			for (String s : uniqCallees) {
				if (!first) {
					summary.append(", ");
				}
				summary.append(jstr(s));
				first = false;
			}
			summary.append("], \"callers\": [");
			first = true;
			for (String s : uniqCallers) {
				if (!first) {
					summary.append(", ");
				}
				summary.append(jstr(s));
				first = false;
			}
			summary.append("], \"error\": " + jstr(error) + "}");
		}

		PrintWriter sw = new PrintWriter(new FileWriter(new File(out, "summary.json"), false));
		try {
			sw.print("{\n\"program\": " + jstr(currentProgram.getName())
					+ ",\n\"image_base\": " + jstr("0x" + Long.toHexString(currentProgram.getImageBase().getOffset()))
					+ ",\n\"targets\": " + addrs.size()
					+ ",\n\"decompiled\": " + ok
					+ ",\n\"failed\": " + fail
					+ ",\n\"functions\": [\n  " + summary + "\n]\n}\n");
		} finally {
			sw.close();
		}

		decomp.dispose();
		println("SotnExportPostScript: decompiled " + ok + "/" + addrs.size()
				+ " (failed " + fail + ") into " + outDir);
	}
}
