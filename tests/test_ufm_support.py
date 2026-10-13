import copy
from pathlib import Path
import struct
import tempfile
import unittest

from maxvell import models
from maxvell.decode import decode as decode_pof
from maxvell.ufm_support import decode, offsets


def _write_pattern(payload, positions, word):
    for position, bit in zip(positions, word):
        mask = 1 << (position % 8)
        if bit == "1":
            payload[position // 8] |= mask
        else:
            payload[position // 8] &= ~mask


class UfmSupportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.support = models.load("5M1270ZT144C5", "ufm_source_sink_support")[0]
        cls.candidates = models.load("5M1270ZT144C5", "ufm_candidates")[0]

    def test_all_source_sink_patterns_keep_support_boundary(self):
        provider = self.support
        expected_sinks = {word: name for name, word in provider["sink_codewords"].items()}
        edge_count = disconnected_count = 0
        for source_word in ("00", "01", "10", "11"):
            for sink_value in range(32):
                sink_word = f"{sink_value:05b}"
                payload = bytearray(208896 // 8)
                _write_pattern(payload, provider["source_offsets"], source_word)
                _write_pattern(payload, provider["sink_offsets"], sink_word)
                result = decode(provider, payload)
                expected_sink = expected_sinks.get(sink_word)
                with self.subTest(source=source_word, sink=sink_word):
                    if expected_sink is None:
                        self.assertEqual(result["status"], "unmatched_sink_codeword")
                    elif source_word not in ("01", "10"):
                        self.assertEqual(result["status"], "unmatched_source_codeword")
                    elif source_word == "10":
                        self.assertEqual(result["status"], "decoded_disconnected_no_edge")
                        disconnected_count += 1
                    else:
                        self.assertEqual(result["edge"]["sink_lc"], expected_sink)
                        self.assertEqual(result["edge"]["source_port"], "dataout[0]")
                        self.assertEqual(result["edge"]["sink_port"], "dataa")
                        self.assertTrue(result["edge"]["support_only"])
                        edge_count += 1
                    if source_word != "01" or expected_sink is None:
                        self.assertIsNone(result["edge"])
                    self.assertFalse(result["canonical_functional_ir_allowed"])
                    self.assertFalse(result["productive_emission_allowed"])
                    self.assertFalse(result["complete_routes_proved"])
                    self.assertFalse(result["event_behavior_proved"])
        self.assertEqual((edge_count, disconnected_count), (4, 4))

    def test_exact_scope_and_geometry_are_enforced(self):
        for key, value in (("target", "5M570ZT144C5"), ("cfm_bits", 208800),
                           ("bit_offset_domain", "packet_0x0011_payload"),
                           ("productive_emission_allowed", True),
                           ("canonical_functional_ir_allowed", True)):
            changed = copy.deepcopy(self.support)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                decode(changed, bytes(208896 // 8))
        for payload in (b"", bytes(208896 // 8 - 12), bytes(208896 // 8 + 12)):
            with self.assertRaisesRegex(ValueError, "geometry"):
                decode(self.support, payload)
        changed = copy.deepcopy(self.support)
        changed["sink_offsets"][1] = changed["sink_offsets"][0]
        with self.assertRaisesRegex(ValueError, "offset"):
            offsets(changed)
        self.assertEqual(offsets(self.support), {133956, 134964, 104489, 101408, 133435, 190724, 190736})

    def test_all_fingerprint_matches_create_no_bindings(self):
        provider = self.candidates
        payload = bytearray(208896 // 8)
        for binding in provider["input_bindings"]:
            _write_pattern(payload, binding["bit_offsets"], binding["codeword"])
        result = decode(provider, payload)
        self.assertEqual(result["matched_input_patterns"], 11)
        self.assertEqual(sum(len(x["bit_offsets"]) for x in provider["input_bindings"]), 2837)
        self.assertEqual(provider["new_input_offset_count"], 2809)
        self.assertEqual((result["bindings_created"], result["edges_created"], result["logical_nets_created"]), (0, 0, 0))
        for flag in ("exact_input_scope_verified", "canonical_support_ir_allowed",
                     "canonical_functional_ir_allowed", "productive_emission_allowed"):
            self.assertFalse(result[flag])
        self.assertTrue(all(x["pattern_matches"] for x in result["input_candidates"]))

    def test_one_fingerprint_counterexample_does_not_gain_a_binding(self):
        provider = self.candidates
        payload = bytearray(208896 // 8)
        for binding in provider["input_bindings"]:
            _write_pattern(payload, binding["bit_offsets"], binding["codeword"])
        changed_binding = provider["input_bindings"][0]
        position = changed_binding["bit_offsets"][0]
        payload[position // 8] ^= 1 << (position % 8)
        result = decode(provider, payload)
        self.assertEqual(result["matched_input_patterns"], 10)
        observed = next(x for x in result["input_candidates"] if x["input_id"] == changed_binding["input_id"])
        self.assertFalse(observed["pattern_matches"])
        self.assertEqual(result["bindings_created"], 0)

    def test_each_profile_endpoint_is_only_a_diagnostic_candidate(self):
        provider = self.candidates
        expected = {"000": "disconnected", "001": "dataout", "010": "data_valid", "011": "nbusy", "100": "osc"}
        for profile in provider["source_profiles"]:
            for word_value in range(8):
                word = f"{word_value:03b}"
                payload = bytearray(208896 // 8)
                _write_pattern(payload, profile["bit_offsets"], word)
                result = decode(provider, payload)
                row = next(x for x in result["source_candidates"] if x["profile_id"] == profile["profile_id"])
                with self.subTest(profile=profile["profile_id"], word=word):
                    self.assertEqual(row["candidate_endpoint"], expected.get(word))
                    self.assertEqual(row["pattern_matches"], word in expected)
                    self.assertFalse(result["exact_input_scope_verified"])
                    self.assertFalse(result["canonical_support_ir_allowed"])
                    self.assertEqual(result["edges_created"], 0)

    def test_diagnostic_scope_cannot_be_promoted_or_overlapped(self):
        for key in ("exact_input_scope_verified", "canonical_support_ir_allowed",
                    "generic_selector_field_allowed", "coordinate_relative_generalization_allowed",
                    "sink_connectivity_edge_allowed"):
            provider = copy.deepcopy(self.candidates)
            provider[key] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                offsets(provider)
        provider = copy.deepcopy(self.candidates)
        provider["input_bindings"][1]["bit_offsets"][0] = provider["input_bindings"][0]["bit_offsets"][0]
        with self.assertRaisesRegex(ValueError, "overlapping"):
            offsets(provider)

    def test_fresh_pof_uses_section_offsets_for_both_stages(self):
        payload = bytearray(208896 // 8)
        _write_pattern(payload, self.support["source_offsets"], "01")
        _write_pattern(payload, self.support["sink_offsets"], "00000")
        prefix = bytearray(b"\xff" * 12)
        struct.pack_into("<I", prefix, 6, 208896)
        packets = [(2, b"5M1270ZT144C5\0"), (17, bytes(prefix) + payload)]
        raw = b"POF\0" + struct.pack("<II", 1, len(packets))
        raw += b"".join(struct.pack("<HI", tag, len(data)) + data for tag, data in packets)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "synthetic.pof"
            path.write_bytes(raw)
            result = decode_pof(path, ["ufm_source_sink_support", "ufm_candidates"])
        support = result["stages"]["ufm_source_sink_support"]
        candidates = result["stages"]["ufm_candidates"]
        self.assertEqual(support["source_codeword"], "01")
        self.assertEqual(support["edge"]["sink_lc"], "LC_X10_Y4_N7")
        self.assertFalse(support["canonical_functional_ir_allowed"])
        self.assertEqual(len(candidates["input_candidates"]), 11)
        self.assertEqual(len(candidates["source_candidates"]), 5)
        self.assertFalse(candidates["exact_input_scope_verified"])
        self.assertEqual(candidates["bindings_created"], 0)


if __name__ == "__main__":
    unittest.main()
