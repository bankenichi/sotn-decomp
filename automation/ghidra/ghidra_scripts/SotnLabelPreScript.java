/* Ghidra preScript for the SOTN stub evidence pilot.
 *
 * Runs BEFORE auto-analysis, so the labels and forced function starts it
 * creates steer analysis instead of fighting it.
 *
 * Args: <symbolFile(s)...> <> <targetAddrFile>  -> headless passes them in
 * order; the runner invokes:
 *   SotnLabelPreScript.java <symFile> <targetFile>
 *
 * symbol file format (splat):   Name = 0x801xxxxx;
 * target file format (ours):    0xADDR NAME ; optional comment
 *
 * Behaviour:
 *   - every symbol inside [imageBase, imageBase + 0xA0000) becomes a label
 *     (data symbols, already-matched functions, everything),
 *   - every target line is disassembled with flow following and forced into
 *     an existing-or-new Function so decompilation has an entry,
 *   - target addresses are excluded from plain label creation to avoid a
 *     duplicate label on top of the function's own plate.
 */

import java.io.BufferedReader;
import java.io.FileReader;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;

public class SotnLabelPreScript extends GhidraScript {

	private static final Pattern SYMBOL = Pattern
			.compile("([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*(0x[0-9A-Fa-f]+)");

	/** "0xADDR NAME ; rest" */
	private static final Pattern TARGET = Pattern
			.compile("^(0x[0-9A-Fa-f]+)\\s+([A-Za-z_][A-Za-z0-9_]*)");

	@Override
	public void run() throws Exception {
		String[] args = getScriptArgs();
		if (args.length < 2) {
			throw new IllegalArgumentException(
					"usage: SotnLabelPreScript.java <symFile> <targetFile>");
		}
		String symFile = args[0];
		String targetFile = args[1];

		long base = currentProgram.getImageBase().getOffset();
		println("SotnLabelPreScript: image base 0x" + Long.toHexString(base));

		// targets first: their addresses get functions with proper names, and
		// the label loop below must skip them
		Set<Long> targetAddrs = new HashSet<Long>();
		int targets = 0;
		BufferedReader tin = new BufferedReader(new FileReader(targetFile));
		try {
			String line;
			while ((line = tin.readLine()) != null) {
				Matcher m = TARGET.matcher(line.trim());
				if (!m.find()) {
					continue;
				}
				long addr = Long.parseLong(m.group(1).substring(2), 16);
				targetAddrs.add(addr);
				targets++;
			}
		} finally {
			tin.close();
		}
		println("SotnLabelPreScript: " + targets + " targets in " + targetFile);

		Map<Long, String> symbols = new LinkedHashMap<Long, String>();
		BufferedReader in = new BufferedReader(new FileReader(symFile));
		try {
			String line;
			while ((line = in.readLine()) != null) {
				Matcher m = SYMBOL.matcher(line);
				if (m.find()) {
					long addr = Long.parseLong(m.group(2).substring(2), 16);
					if (!symbols.containsKey(addr)) {
						symbols.put(addr, m.group(1));
					}
				}
			}
		} finally {
			in.close();
		}

		int labels = 0;
		int skipped = 0;
		for (Map.Entry<Long, String> e : symbols.entrySet()) {
			long addr = e.getKey();
			// each US overlay owns [0x80180000, +640 KiB); never import other
			// overlays' symbols into this program (their vram window overlaps)
			if (addr < base || addr >= base + 0xA0000) {
				skipped++;
				continue;
			}
			if (targetAddrs.contains(addr)) {
				continue; // function creation below names these
			}
			try {
				createLabel(toAddr(addr), e.getValue(), true);
				labels++;
			} catch (Exception ex) {
				println("SotnLabelPreScript: label " + e.getValue()
						+ " failed: " + ex.getMessage());
			}
		}
		println("SotnLabelPreScript: " + labels + " labels created, "
				+ skipped + " symbols outside window");

		int funcs = 0;
		BufferedReader tin2 = new BufferedReader(new FileReader(targetFile));
		try {
			String line;
			while ((line = tin2.readLine()) != null) {
				Matcher m = TARGET.matcher(line.trim());
				if (!m.find()) {
					continue;
				}
				long addr = Long.parseLong(m.group(1).substring(2), 16);
				String name = m.group(2);
				Address a = toAddr(addr);

				DisassembleCommand cmd = new DisassembleCommand(a, null, true);
				cmd.applyTo(currentProgram, monitor);

				Function f = getFunctionAt(a);
				if (f == null) {
					f = createFunction(a, name);
					if (f == null) {
						println("SotnLabelPreScript: FAILED to create function "
								+ name + " at 0x" + Long.toHexString(addr));
					}
				} else {
					// refresh the plate name to the stub symbol
					try {
						f.setName(name, ghidra.program.model.symbol.SourceType.USER_DEFINED);
					} catch (Exception ex) {
						// non-fatal; the existing plate is already meaningful
					}
				}
				funcs++;
			}
		} finally {
			tin2.close();
		}
		println("SotnLabelPreScript: " + funcs + " target functions prepared");
	}
}
