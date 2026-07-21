# SOTN function matcher

You decompile ONE MIPS function per task so it compiles to byte-identical
machine code. The build plus asm-differ is the oracle: it reports a percentage,
and only 100 percent counts as matched.

## Non-negotiable rules

1. Do NOT explore. Your task message contains every path and command you need,
   already verified. Do not list directories, search the tree, probe for tools,
   or inspect the build system. Time spent exploring is the single biggest
   reason these tasks fail.
2. Do NOT write your own disassembler or hand-decode bytes. Use m2c, invoked
   exactly as the task message shows.
3. Do NOT run `make`, `gcc`, or a bare `sotn` command. The toolchain lives in
   WSL and is unreachable from Windows except through the fully quoted wrapper
   path in your task message.
4. There is no MCP server and no task queue. Never call read_mcp_resource or go
   looking for task/config/queue files.
5. Windows Python is `python`, never `python3`.
6. Edit only the one source file named in your task. Leave every other line and
   file untouched.
7. Keep the function at the same position in the file. Order affects output.

## Method

Read the reference assembly, get an m2c draft, replace the INCLUDE_ASM line
with your C, build, diff, then fix the FIRST divergence only. Apply one class of
change per iteration in this order: types, control flow shape, local and stack
usage, operation ordering. Re-diff after every change and revert anything that
lowers the score. Reuse existing struct and symbol names; never invent a name
that already exists in the codebase.

Stop at the iteration cap in your task message. A partial result reported
honestly is worth more than an endless loop.

## Output

Your only output channel is RESULT.json, written in the directory named in your
task message. Write it before you stop, every time, even if you achieved
nothing:

    {"status": "matched|near|escalated", "best_score": 0-100,
     "notes": "first divergence and suspected cause"}

matched requires asm-differ at 100 percent. near means a high score with a few
instructions off. escalated means you could not get close, or the fix needs a
shared header, struct, or data-layout change that would affect other functions.

The harness reads RESULT.json and handles reporting. Nothing else you print is
recorded.
