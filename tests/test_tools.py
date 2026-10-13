"""Synthetic behavior and fail-closed boundaries; no original input files."""
import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
from maxvell import models
from maxvell.cli import demo
from maxvell.decode import decode,decode_lut,decode_semantic_lut,decode_ufm,inspect
from maxvell.emit import emit_lut
from maxvell.analysis import analyze
from maxvell.simulation import simulate
from maxvell._core.pof import load_pof,crc16_x25
from maxvell._core.native_user_code_storage import decode_provider
from maxvell._core.native_route_predicate_frontier import compile_predicates,evaluate
from maxvell._core.native_candidate_path import CandidateGraph
from maxvell.validation import privacy_categories

TARGET="5M40ZE64C5"

def pof_bytes(target=TARGET,payload=None,extras=(),crc=False):
    if payload is None:payload=bytes(53248//8)
    header=bytearray(12);struct.pack_into("<I",header,6,len(payload)*8)
    packets=[(2,target.encode()+b"\0"),(17,bytes(header)+payload),*extras]
    if crc:packets.append((8,b"\0\0"))
    data=b"POF\0"+struct.pack("<II",1,len(packets))+b"".join(struct.pack("<HI",tag,len(raw))+raw for tag,raw in packets)
    if crc:data=data[:-2]+struct.pack("<H",crc16_x25(data[:-2]))
    return data

class ToolsTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
    def input(self,data):
        p=self.root/"input.pof";p.write_bytes(data);return p

    def test_snapshot_scopes(self):
        status=models.status()
        self.assertEqual(status["metadata"]["format"],"maxvell.results.v2")
        self.assertNotIn("source_revision",status["metadata"])
        self.assertEqual(status["counts"]["model_catalog"],1363)
        self.assertFalse(status["public_productive_grant"])
    def test_privacy_patterns_and_regex_false_positives(self):
        fixtures=["Z"+":"+"/project/file", "\\"*2+"host"+"\\share\\file", "test"+"@"+"example.invalid", ".".join(["192","0","2","1"])]
        for text in fixtures:self.assertTrue(privacy_categories(text))
        self.assertFalse(privacy_categories("https://example.org/resource"))
        self.assertFalse(privacy_categories(r"LC_X(\\d+)_Y(\\d+)"))
    def test_crc_standard_vector_and_input_snapshot(self):
        self.assertEqual(crc16_x25(b"123456789"),0x906E)
        raw=pof_bytes(crc=True);p=self.input(raw)
        parsed=load_pof(p,data=raw);p.write_bytes(b"changed")
        self.assertTrue(parsed.terminator_crc().crc_ok)
    def test_bad_crc_rejected(self):
        raw=bytearray(pof_bytes(crc=True));raw[100]^=1
        with self.assertRaisesRegex(ValueError,"CRC"):inspect(self.input(raw))
    def test_truncated_and_trailing_container_rejected(self):
        for raw in (b"POF\0",pof_bytes()[:-1],pof_bytes()+b"extra"):
            with self.subTest(length=len(raw)),self.assertRaises(ValueError):inspect(self.input(raw))
    def test_duplicate_critical_packet_rejected(self):
        for extra in (((2,TARGET.encode()),),((8,b"\0\0"),(8,b"\0\0"))):
            with self.subTest(extra=extra),self.assertRaises(ValueError):inspect(self.input(pof_bytes(extras=extra)))
    def test_geometry_and_exact_target_rejected(self):
        for data in (pof_bytes(target="5M40Z"),pof_bytes(payload=b"\0")):
            with self.assertRaises(ValueError):decode(self.input(data),["lut"])
    def test_metadata_does_not_escape_summary(self):
        raw=pof_bytes(extras=((1,b"temporary operator"),(3,b"local note")))
        p=self.input(raw);_,summary=inspect(p)
        text=json.dumps(summary)
        for excluded in (str(p),"temporary operator","local note"):
            self.assertNotIn(excluded,text)
    def test_usercode_bit_order_and_polarity(self):
        provider,record=models.load(TARGET,"usercode");payload=bytearray(record["cfm_bits"]//8)
        expected=0x96A5C33C
        for ordinal,offset,xor in provider["bindings"]:
            payload[offset//8]|=(((expected>>ordinal)&1)^xor)<<(offset%8)
        result=decode_provider(provider,payload)
        self.assertEqual(result["value"],expected)
        self.assertFalse(result["productive_emission_allowed"])
    def test_native_lut_applies_serializer_xor(self):
        provider,_=models.load(TARGET,"lut")
        changed=copy.deepcopy(provider);changed["rows"][0]["native_serializer_xor"]^=1
        before={r["native_location"]:r["native_ordinal_mask"] for r in decode_lut(provider,bytes(53248//8))}
        after={r["native_location"]:r["native_ordinal_mask"] for r in decode_lut(changed,bytes(53248//8))}
        row=provider["rows"][0];location=row["lc_location"]
        self.assertEqual(int(before[location],16)^int(after[location],16),1<<row["asmdb_lut_ordinal"])
    def test_duplicate_lut_offset_rejected(self):
        provider,_=models.load(TARGET,"lut");provider["rows"][1]["pof_payload_offset"]=provider["rows"][0]["pof_payload_offset"]
        with self.assertRaises(ValueError):decode_lut(provider,bytes(53248//8))
    def test_unavailable_stage_and_ufm_rejected(self):
        p=self.input(pof_bytes())
        for stage in ("unknown","ufm_content"):
            with self.assertRaises(ValueError):decode(p,[stage])
    def test_ufm_word_mapping(self):
        provider,_=models.load("*","ufm_content");payload=bytearray(1024);layout=provider["layout"]
        expected=[(word*257)^0xA596 for word in range(512)]
        expected=[v&0xFFFF for v in expected]
        for i,offset in enumerate(layout["offset_by_logical_bit"]):
            bit=((expected[i//16]>>(i%16))&1)^layout["xor_by_logical_bit"][i]
            payload[offset//8]|=bit<<(offset%8)
        self.assertEqual(decode_ufm(payload,provider)["words"],expected)
        ir=decode(self.input(pof_bytes(extras=((24,b"\0"*6+struct.pack("<I",8192)+b"\0"*2+payload),))),["ufm_content"])
        self.assertEqual(ir["stages"]["ufm_content"]["words"],expected)
    def test_ufm_alias_rejected(self):
        provider,_=models.load("*","ufm_content");provider["layout"]["offset_by_logical_bit"][1]=provider["layout"]["offset_by_logical_bit"][0]
        with self.assertRaises(ValueError):decode_ufm(bytes(1024),provider)
    def test_demo_truth_table_and_emission(self):
        result=demo(self.root/"demo")
        self.assertEqual(result["logical_mask"],"6996")
        ir=json.loads((self.root/"demo/storage_ir.json").read_text())
        self.assertEqual(ir["logical_nets_created"],0)
        verilog=(self.root/"demo/partial_project/cells.v").read_text()
        self.assertIn("MASK[unresolved_native_input]",verilog)
        for index in range(16):self.assertEqual((0x6996>>index)&1,index.bit_count()%2)
    def test_invalid_emission_writes_no_files(self):
        demo(self.root/"demo");ir=json.loads((self.root/"demo/storage_ir.json").read_text())
        for change in ({"target":"5M160ZE64C5"},{"productive_emission_allowed":True}):
            with self.assertRaises(ValueError):emit_lut({**ir,**change},self.root/"invalid")
            self.assertFalse((self.root/"invalid").exists())
    def test_route_ambiguity_is_not_collapsed(self):
        resources={1:[1,43,2,1,0,0,0],2:[2,43,2,1,0,1,0],3:[3,276,2,1,0,0,0]}
        fields=[{"source_gid":i,"sink_gid":3,"group":0,"bits":[[10+i,0,-1]]} for i in (1,2)]
        rows=compile_predicates(fields,{1:[],2:[]},{11:(0,0),12:(1,0)},8)
        r=evaluate(rows,b"\3",resources)
        self.assertEqual(r["sink_results"][0]["destination_state"],"multiple")
        self.assertFalse(r["selected_routes_proved"])
        graph=CandidateGraph(list(resources.values()),r["sink_results"])
        self.assertEqual(graph.trace(3)["status"],"unresolved_destination")
    def test_native_candidate_analysis_boundaries(self):
        result=analyze(self.input(pof_bytes()))
        self.assertGreater(result["routes"]["pair_count"],0)
        self.assertEqual(len(result["controls"]),240)
        self.assertFalse(result["named_port_order_proved"])
        self.assertFalse(result["productive_emission_allowed"])
    def test_sequential_simulation_updates_on_rising_edge(self):
        model={"format":"maxvrec.native_sequential_cone.v1","inputs":["clock","data"],"cells":{},"registers":{"q":{"clock_edge":"rising","clock_pin":"clock","data":{"kind":"input_pin","pin":"data"}}},"pins":[{"pin":"out","mode":"push_pull","data":{"kind":"register","native_lc":"q"},"oe":{"kind":"constant","value":1}}]}
        stimulus={"initial_state":{"q":0},"initial_inputs":{"clock":0,"data":0},"input_steps":[{"clock":0,"data":1},{"clock":1,"data":1},{"clock":1,"data":0},{"clock":0,"data":0},{"clock":1,"data":0}]}
        result=simulate(model,stimulus)
        self.assertEqual([r["state"]["q"] for r in result["steps"]],[0,1,1,1,0])
        self.assertFalse(result["independent_equivalence_proved"])

if __name__=="__main__":unittest.main()
