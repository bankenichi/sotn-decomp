/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:BOSS/BO6:BO6_AguneaShuffleParams
   attempt: 4/4
   model  : opencode/nemotron-3-ultra-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:

   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
void BO6_AguneaShuffleParams(s32 bufSize, s32* buf) {
    // Fisher-Yates shuffle of buf[0..bufSize-1] for Agunea boss attack pattern randomization
    s32 i = bufSize - 1;
    if (i > 0) {
        s32* current = buf + i;  // Start from last element
        do {
                s32 temp;
                s32 *randPtr;
            i--;
            temp = *current;
            randPtr = buf + (rand() % bufSize);
            *current = *randPtr;                    // Swap current with random
            current--;                              // Move to previous element
            *randPtr = temp;                        // Complete swap (in branch delay slot)
        } while (i > 0);
    }
}