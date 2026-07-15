import hashlib
import json
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "reference" / "core-contracts.json"
PIPELINE_LAYOUTS = ROOT / "reference" / "pipeline-layouts.tsv"
MANIFEST = ROOT / "reference" / "manifest.lock"


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )


def lock_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value
    return values


def pipeline_layouts() -> list[dict[str, str | int]]:
    layouts: list[dict[str, str | int]] = []
    for line_number, raw in enumerate(PIPELINE_LAYOUTS.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        columns = raw.split("\t")
        if len(columns) != 8:
            raise AssertionError(f"{PIPELINE_LAYOUTS}:{line_number}: expected 8 columns")
        bus, path, expression, scala_name, high, low, provenance, source_commit = columns
        layouts.append(
            {
                "bus": bus,
                "path": path,
                "expression": expression,
                "scala_name": scala_name,
                "high": int(high),
                "low": int(low),
                "provenance": provenance,
                "source_commit": source_commit,
            }
        )
    return layouts


def parse_commented_concat(source: str, bus: str) -> list[tuple[str, int, int]]:
    match = re.search(rf"assign\s+{re.escape(bus)}\s*=\s*\{{(.*?)\}};", source, re.DOTALL)
    if match is None:
        raise AssertionError(f"missing assign for {bus}")
    fields: list[tuple[str, int, int]] = []
    for raw in match.group(1).splitlines():
        comment = re.search(r"//\s*(\d+)\s*:\s*(\d+)", raw)
        if comment is None:
            continue
        expression = raw.split("//", 1)[0].strip().rstrip(",").strip()
        fields.append((re.sub(r"\s+", "", expression), int(comment.group(1)), int(comment.group(2))))
    return fields


def parse_lacc_prefix(source: str) -> list[str]:
    match = re.search(r"assign\s+ds_to_es_bus\s*=\s*\{(.*?)\};", source, re.DOTALL)
    if match is None:
        raise AssertionError("missing assign for ds_to_es_bus")
    prefix = match.group(1).split("inst_csr_rstat_en", 1)[0]
    expressions = []
    for raw in prefix.splitlines():
        line = raw.strip()
        if not line or line.startswith("`if") or line.startswith("`end"):
            continue
        expression = line.split("//", 1)[0].strip().rstrip(",").strip()
        if expression:
            expressions.append(re.sub(r"\s+", "", expression))
    return expressions


def layout_digest(records: list[dict[str, str | int]], *buses: str) -> str:
    least_to_most = []
    for bus in buses:
        least_to_most.extend(reversed([record for record in records if record["bus"] == bus]))
    canonical = "".join(
        f"{record['scala_name']}:{record['high']}:{record['low']}\n" for record in least_to_most
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class CoreContractManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.golden = cls.document["golden_commit"]

    def source(self, path: str) -> str:
        return git("show", f"{self.golden}:{path}").stdout

    def test_locked_source_blobs_exist(self) -> None:
        for source in self.document["sources"]:
            actual = git("rev-parse", f"{self.golden}:{source['path']}").stdout.strip()
            self.assertEqual(source["blob_sha1"], actual, source["path"])

    def test_pipeline_width_comments_anchor_the_four_layouts(self) -> None:
        anchors = {
            "rtl/if_stage.v": ("assign fs_to_ds_bus", 108),
            "rtl/id_stage.v": ("assign ds_to_es_bus", 349),
            "rtl/exe_stage.v": ("assign es_to_ms_bus", 424),
            "rtl/mem_stage.v": ("assign ms_to_ws_bus", 492),
        }
        expected = self.document["pipeline_widths"]
        self.assertEqual(anchors["rtl/if_stage.v"][1] + 1, expected["fetch"])
        self.assertEqual(anchors["rtl/id_stage.v"][1] + 1, expected["decode_lacc_off"])
        self.assertEqual(anchors["rtl/exe_stage.v"][1] + 1, expected["execute"])
        self.assertEqual(anchors["rtl/mem_stage.v"][1] + 1, expected["memory"])
        for path, (assignment, high_bit) in anchors.items():
            text = self.source(path)
            start = text.index(assignment)
            excerpt = text[start : start + 800]
            self.assertRegex(excerpt, rf"//\s*{high_bit}:")

    def test_pipeline_layout_oracle_is_parsed_from_golden_concats(self) -> None:
        records = pipeline_layouts()
        buses = {
            "fetch": ("rtl/if_stage.v", "fs_to_ds_bus"),
            "decode_base": ("rtl/id_stage.v", "ds_to_es_bus"),
            "execute": ("rtl/exe_stage.v", "es_to_ms_bus"),
            "memory": ("rtl/mem_stage.v", "ms_to_ws_bus"),
        }
        for oracle_bus, (path, verilog_bus) in buses.items():
            expected = [
                (record["expression"], record["high"], record["low"])
                for record in records
                if record["bus"] == oracle_bus
            ]
            actual = parse_commented_concat(self.source(path), verilog_bus)
            self.assertEqual(expected, actual, oracle_bus)
            for record in (record for record in records if record["bus"] == oracle_bus):
                self.assertEqual(path, record["path"])
                self.assertEqual("golden_comment", record["provenance"])
                self.assertEqual(self.golden, record["source_commit"])

    def test_lacc_prefix_uses_locked_upstream_width_not_missing_comments(self) -> None:
        records = [record for record in pipeline_layouts() if record["bus"] == "decode_lacc_prefix"]
        lacc = self.document["lacc"]
        self.assertEqual(
            [record["expression"] for record in records],
            parse_lacc_prefix(self.source("rtl/id_stage.v")),
        )
        self.assertEqual(["ds_inst[22+:`LACC_OP_WIDTH]", "lacc_req"], [r["expression"] for r in records])
        self.assertEqual(3, lacc["operation_count"])
        self.assertEqual(2, lacc["operation_width"])
        base_high = self.document["pipeline_widths"]["decode_lacc_off"] - 1
        expected_ranges = [
            (base_high + 1 + lacc["operation_width"], base_high + 2),
            (base_high + 1, base_high + 1),
        ]
        self.assertEqual(expected_ranges, [(r["high"], r["low"]) for r in records])
        for record in records:
            self.assertEqual("locked_upstream_macro", record["provenance"])
            self.assertEqual(lacc["source_commit"], record["source_commit"])

    def test_scala_layout_digests_are_derived_from_the_verified_oracle(self) -> None:
        records = pipeline_layouts()
        expected = {
            "fetch": layout_digest(records, "fetch"),
            "decode_base": layout_digest(records, "decode_base"),
            "decode_lacc": layout_digest(records, "decode_base", "decode_lacc_prefix"),
            "execute": layout_digest(records, "execute"),
            "memory": layout_digest(records, "memory"),
        }
        spec = (
            ROOT / "spinal" / "src" / "test" / "scala" / "openla500" / "pipeline" / "PipelinePayloadsSpec.scala"
        ).read_text(encoding="utf-8")
        actual = dict(re.findall(r'"(fetch|decode_base|decode_lacc|execute|memory)"\s*->\s*"([0-9a-f]{64})"', spec))
        self.assertEqual(expected, actual)

    def test_lacc_width_and_provenance_are_explicit(self) -> None:
        widths = self.document["pipeline_widths"]
        lacc = self.document["lacc"]
        self.assertEqual(
            widths["decode_lacc_on"],
            widths["decode_lacc_off"] + 1 + lacc["operation_width"],
        )
        self.assertEqual(3, lacc["operation_count"])
        self.assertEqual(lock_values()["openla500_upstream"], lacc["source_commit"])
        missing_header = git("cat-file", "-e", f"{self.golden}:rtl/mycpu.h", check=False)
        self.assertNotEqual(0, missing_header.returncode)
        self.assertFalse(lacc["candidate_tree_has_header"])

    def test_locked_header_and_config_match_manifest(self) -> None:
        values = lock_values()
        header = self.document["locked_chiplab_header"]
        self.assertEqual(values["chiplab_mycpu_gitlink"], header["mycpu_gitlink"])
        self.assertEqual(self.document["pipeline_widths"]["fetch"], header["pipeline_widths"]["fetch"])
        self.assertEqual(
            self.document["pipeline_widths"]["decode_lacc_off"],
            header["pipeline_widths"]["decode_lacc_off"],
        )

    def test_predictor_and_cache_geometry_are_present_in_golden(self) -> None:
        config = self.document["locked_config"]
        btb = self.source("rtl/btb.v")
        self.assertEqual(32, config["btb_entries"])
        self.assertIn("parameter BTBNUM = 64", btb)
        official = self.document["official_behavioral_source"]
        self.assertEqual("aa3bde1f3e720e71c2c78d6b81930d797b810149", official["commit"])
        self.assertEqual("e2f6e340c1f4f98ce93493192030c32943935229", official["btb_git_blob_sha1"])
        self.assertEqual(
            "6d540a983075e8ed3a9bd1f791bc4ec14e3b08ff04c4c8f13ae1c0fa8a081bfb",
            official["btb_sha256"],
        )
        self.assertRegex(btb, rf"parameter\s+RASNUM\s*=\s*{config['ras_entries']}")
        for cache_path, cache in (("rtl/icache.v", config["i_cache"]), ("rtl/dcache.v", config["d_cache"])):
            text = self.source(cache_path)
            self.assertIn("way_bank_addra [1:0][3:0]", text)
            self.assertRegex(text, r"input\s+\[\s*7:0\]\s+index")
            self.assertEqual(256, cache["sets"])
            self.assertEqual(2, cache["ways"])
            self.assertEqual(16, cache["line_bytes"])


if __name__ == "__main__":
    unittest.main()
