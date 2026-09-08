"""Behavioral data search, ownership, corruption and frozen-replay checks."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from automation import data_search as ds
from automation.search_archive import ContentAddressedArchive, ArtifactCorrupt


class DataSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        (self.repo / "config").mkdir()
        self.pattern = bytes(range(8))
        self.config("sta", b"A" * 8 + self.pattern + b"a" * 8, 8, "thing")
        self.config("stb", b"B" * 8 + self.pattern + b"b" * 8, 8, "thing")
        self.config("sttarget", b"T" * 8 + self.pattern + b"t" * 8, 8, None)

    def config(self, name, binary, start, owner, *, kind="data"):
        path = self.repo / (name + ".bin")
        path.write_bytes(binary)
        data = {"sha1": hashlib.sha1(binary).hexdigest(), "options": {"target_path": path.name},
                "segments": [{"start": 0, "vram": 4096, "subsegments":
                              [[0, "c", "first"], [start, kind] + ([owner] if owner else []),
                               [start + 8, "c", "last"]]}, [len(binary)]]}
        config = self.repo / "config" / ("splat.us." + name + ".yaml")
        config.write_text(yaml.safe_dump(data, default_flow_style=None))
        return config

    def run_search(self, run="test"):
        return ds.search(self.repo, run, version="us", target="sttarget", stem="thing")

    def test_real_bytes_calibrate_and_frozen_retry_does_not_read_live_inputs(self):
        result = self.run_search()
        self.assertEqual(result["funnel"]["eligible"], 1)
        self.assertEqual(result["candidates"][0]["range"], {"start": 8, "end": 16, "ownership": "inferred"})
        self.assertEqual(result["landing_status"], "not_attempted")
        (self.repo / "sttarget.bin").write_bytes(b"changed")
        with patch.object(ds, "_snapshot", side_effect=AssertionError("live rescan")):
            self.assertEqual(self.run_search(), result)
            self.assertEqual(ds.verify(self.repo / ds.STORE / "test"), result)

    def test_unrelated_named_owner_and_code_are_not_search_space(self):
        self.config("sttarget", b"T" * 8 + self.pattern + b"t" * 8, 8, "other")
        self.assertEqual(self.run_search()["funnel"]["eligible"], 0)
        self.config("sttarget", b"T" * 8 + self.pattern + b"t" * 8, 8, "thing", kind="c")
        self.assertEqual(self.run_search("code")["funnel"]["measured"], 0)

    def test_duplicate_binary_is_not_independent_calibration(self):
        self.config("stb", b"A" * 8 + self.pattern + b"a" * 8, 8, "thing")
        result = self.run_search()
        self.assertEqual(result["dispositions"][0]["status"], "insufficient_independent_peers")

    def test_repeated_hits_are_retained_but_never_eligible(self):
        cfg = self.config("sttarget", b"T" * 8 + self.pattern * 2 + b"t" * 8, 8, None)
        doc = yaml.safe_load(cfg.read_text())
        doc["segments"][0]["subsegments"][2][0] = 24
        cfg.write_text(yaml.safe_dump(doc))
        result = self.run_search()
        self.assertEqual(result["dispositions"][0]["hits"], [8, 16])
        self.assertEqual(result["funnel"]["eligible"], 0)

    def test_declared_near_candidate_gets_data_score(self):
        self.config("sttarget", b"T" * 8 + b"X" + self.pattern[1:] + b"t" * 8, 8, "thing")
        candidate = self.run_search()["candidates"][0]
        self.assertEqual(candidate["score"]["mismatched_bytes"], 1)
        self.assertFalse(candidate["eligible_for_preparation"])
        self.assertEqual(ds.score_bytes(b"a", b"ab").missing_bytes, 1)
        self.assertEqual(ds.score_bytes(b"abc", b"ab").extra_bytes, 1)

    def test_config_sha_and_archived_binary_corruption_refused(self):
        (self.repo / "sttarget.bin").write_bytes(b"wrong")
        with self.assertRaisesRegex(ds.DataSearchError, "SHA-1"):
            self.run_search()
        self.config("sttarget", b"T" * 8 + self.pattern + b"t" * 8, 8, None)
        self.run_search()
        root = self.repo / ds.STORE / "test"
        binary = next((root / "artifacts/binaries").glob("*.bin"))
        binary.write_bytes(b"corrupt")
        with self.assertRaises(ArtifactCorrupt):
            ds.verify(root)

    def test_false_result_cannot_be_verified_even_with_valid_content_address(self):
        self.run_search()
        root = self.repo / ds.STORE / "test"
        result_path = next((root / "artifacts/results").glob("*.json"))
        result = json.loads(result_path.read_text())
        result["funnel"]["eligible"] = 99
        result_path.unlink()  # Corruption simulation in the disposable fixture.
        ContentAddressedArchive(root).put_json(result, category="results")
        with self.assertRaisesRegex(ds.DataSearchError, "independently replayed"):
            ds.verify(root)

    def test_owner_collision_and_foreign_run_reuse_refused(self):
        with self.assertRaisesRegex(ds.DataSearchError, "conflicting"):
            ds.ranges({"segments": [{"start": 0, "subsegments":
                       [[0, "data", "one"], [0, "data", "two"]]}, [8]]}, 8)
        self.run_search()
        with self.assertRaisesRegex(ds.DataSearchError, "another request"):
            ds.search(self.repo, "test", version="us", target="sta", stem="thing")

    def test_config_preparation_splits_only_calibrated_data_range(self):
        from automation.data_landing import _splice_config
        raw = b"segments:\n  - [0x0, data]\n  - [0x30, c, thing]\n"
        revised = _splice_config(raw, 8, 16, "thing")
        self.assertIn(b"[0x8, .data, thing]\n  - [0x10, data]", revised)
        self.assertEqual(revised.replace(b"  - [0x8, .data, thing]\n  - [0x10, data]\n", b""), raw)
        with self.assertRaisesRegex(ds.DataSearchError, "unnamed data owner"):
            _splice_config(raw.replace(b"0x0, data", b"0x0, c, code"), 8, 16, "thing")

    def test_dependency_closure_preserves_rodata_after_local_jump_targets(self):
        from automation.data_dependencies import derive, instructions
        import struct
        archive = ContentAddressedArchive(self.repo / "closure")
        snapshots, entries = [], []
        for name, label, discriminator in (("sttarget", "D_us_00001050", 0), ("sta", "gTable", 1), ("stb", "gTable", 2)):
            words = [0x3C020000, 0x24421050] + [0] * 18
            binary = struct.pack("<20I", *words) + bytes(16) + struct.pack("<4I", 0x1000, 0x1004, 0xDEADBEEF, discriminator)
            rows = []
            for index, word in enumerate(words):
                text = (f"lui $v0, %hi({label})" if index == 0 else
                        f"addiu $v0, $v0, %lo({label})" if index == 1 else
                        "lui $v1, %hi(jtbl_us_00001060)" if index == 2 else "nop")
                rows.append(f"/* {index * 4:X} {0x1000 + index * 4:X} {struct.pack('<I', word).hex()} */ {text}")
            raw = "\n".join(rows).encode()
            cfg = f"config/splat.us.{name}.yaml"
            snapshots.append({"config_path": cfg, "binary": archive.put_object(binary).to_dict(),
                              "ranges": [{"section": "data", "owner": None, "vram": 0x1050, "start": 80, "end": 96},
                                         {"section": "rodata", "owner": None, "vram": 0x1060, "start": 96, "end": 112}]})
            entries.append({"config_path": cfg, "files": [{"function": "F", "artifact": archive.put_bytes(raw).to_dict()}]})
            with self.assertRaisesRegex(ds.DataSearchError, "differs from original"):
                instructions(raw, b"changed")
        request = {"target": "sttarget", "snapshots": snapshots}
        inputs = {"entries": entries, "header": archive.put_source("extern int gTable[4];").to_dict(),
                  "symbols": archive.put_bytes(b"").to_dict()}
        result = derive(request, inputs, archive)
        self.assertEqual(result["tables"], [{"function": "F", "start": 96, "end": 104}])
        self.assertEqual(result["aliases"][0]["address"], 0x1050)
        self.assertEqual(len(result["aliases"][0]["donors"]), 2)
        inputs["entries"] = entries[:2]
        with self.assertRaisesRegex(ds.DataSearchError, "independent consistent"):
            derive(request, inputs, archive)

    def test_preparation_is_bound_to_header_target_and_records(self):
        from automation import data_landing as dl
        from automation.search_full_oracle import TOOL_FILES
        config = self.repo / "config/splat.us.sttarget.yaml"
        document = yaml.safe_load(config.read_text())
        document["options"]["asm_path"] = "asm/us/st/target"
        config.write_text(yaml.safe_dump(document, default_flow_style=None))
        assembly = self.repo / "asm/us/st/target/nonmatchings/thing/F.s"
        assembly.parent.mkdir(parents=True)
        assembly.write_text("glabel F\n/* 0 1000 54545454 */ nop\n")
        (self.repo / "config/symbols.us.sttarget.txt").write_text("")
        self.run_search()
        source = self.repo / "src/st/target/thing.c"
        source.parent.mkdir(parents=True)
        source.write_text('#include "target.h"\nINCLUDE_ASM("st/target/nonmatchings/thing", F);\n')
        header = self.repo / "src/st/thing.h"
        header.write_text('void F(void) { return; }\n')
        (self.repo / "automation").mkdir()
        for name in ("data_search.py", "data_landing.py", "data_dependencies.py", "shim_sweep.py"):
            (self.repo / "automation" / name).write_bytes((ds.ROOT / "automation" / name).read_bytes())
        binding = {"protocol": "sotn-automatic-landing-v1", "policy": "stop_after_first_oracle_attempt",
                   "files": [{"path": name, "content_hash": ds.hash_bytes(b"fixture"), "byte_size": 7}
                             for name in (*TOOL_FILES, "config/check.us.sha")]}
        root = self.repo / ds.STORE / "test"
        with patch("automation.search_full_oracle.capture_binding", return_value=binding):
            intent = dl.prepare(self.repo, root)
        self.assertEqual(intent["records"], ["us:ST/TARGET:F"])
        self.assertEqual(dl.prepare(self.repo, root), intent)
        forged = json.loads(json.dumps(intent))
        forged["changes"][0]["path"] = "src/st/other/thing.c"
        with self.assertRaisesRegex(ds.DataSearchError, "unrelated paths"):
            dl.validate_preparation(forged, ds.verify(root), ContentAddressedArchive(root))


if __name__ == "__main__":
    unittest.main()
