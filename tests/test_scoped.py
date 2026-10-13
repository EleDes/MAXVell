"""Support predicates, retained topology and fail-closed electrical options."""
import copy
import tempfile
import unittest
from pathlib import Path
from maxvell import models
from maxvell.scoped import decode, qsf_lines


def set_bit(payload, offset, value):
    payload[offset//8] = (payload[offset//8] & ~(1 << (offset%8))) | (value << (offset%8))


class ScopedTest(unittest.TestCase):
    def test_candidate_packet_offsets_are_normalized_to_cfm(self):
        from maxvell.coverage import family_offsets
        from maxvell.decode import decode as decode_pof, inspect
        from test_tools import pof_bytes
        provider,_=models.load('5M1270ZT144C5','aload_candidates')
        sites,_=models.load('5M1270ZT144C5','aload_sites')
        payload=bytes((i*73+29)%256 for i in range(provider['cfm_bits']//8))
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'own.pof'
            path.write_bytes(pof_bytes('5M1270ZT144C5',payload))
            pof,_=inspect(path)
            packet=pof.packet(17).payload
            result=decode_pof(path,['aload_candidates'])['stages']['aload_candidates']
            self.assertEqual(result['offset_domain'],'cfm_section_payload_lsb0')
            for original,decoded in zip(provider['candidate_bits'],result['candidate_bits']):
                offset=original['payload_offset']
                self.assertEqual(decoded['packet_payload_offset'],offset)
                self.assertEqual(decoded['payload_offset'],offset-96)
                self.assertEqual(decoded['raw_value'],(packet[offset//8]>>(offset%8))&1)
            self.assertEqual({r['payload_offset'] for r in result['candidate_bits']},
                             {s['payload_offset'] for s in sites['sites']})
            self.assertEqual(family_offsets('5M1270ZT144C5','aload_candidates',provider),
                             {s['payload_offset'] for s in sites['sites']})
            bad=copy.deepcopy(provider)
            bad['candidate_bits'][0]['payload_offset']=95
            from maxvell.scoped import candidate_bindings
            with self.assertRaisesRegex(ValueError,'bindings'):candidate_bindings(bad)

    def test_aload_positive_and_non_hit_boundaries(self):
        p, _ = models.load('5M1270ZT144C5','aload_sites')
        payload = bytearray(p['cfm_bits']//8)
        site = p['sites'][0]
        set_bit(payload,site['lut_offsets'][0],1)
        set_bit(payload,site['payload_offset'],1)
        result = decode('aload_sites',p,payload)
        self.assertEqual(result['observations'],[{'quartus_lc':site['quartus_lc'],'raw_value':1,'connectivity_state':'positive'}])
        self.assertEqual(len(result['edges']),1)
        self.assertFalse(result['source_identity_proved'])
        self.assertFalse(result['canonical_functional_ir_allowed'])
        set_bit(payload,site['payload_offset'],0)
        result = decode('aload_sites',p,payload)
        self.assertEqual(result['observations'][0]['connectivity_state'],'unresolved')
        self.assertEqual(result['edges'],[])
        self.assertFalse(result['negative_means_absent'])
        set_bit(payload,site['lut_offsets'][0],0)
        self.assertEqual(decode('aload_sites',p,payload)['observations'],[])

    def test_topology_permutation_and_no_connectivity_grant(self):
        p, _ = models.load('5M570ZT144C5','lut_topology')
        lc = next(lc for lc,terms in p['cells'].items() if any(t[1]!=t[2] for t in terms))
        term = next(t for t in p['cells'][lc] if t[1]!=t[2])
        payload = bytearray(p['cfm_bits']//8)
        set_bit(payload,term[0],1)
        result = decode('lut_topology',p,payload)
        cell = next(c for c in result['cells'] if c['quartus_lc']==lc)
        self.assertEqual(int(cell['physical_mask'],16),1 << term[1])
        self.assertEqual(int(cell['retained_topology_mask'],16),1 << term[2])
        self.assertFalse(result['input_topology_verified'])
        self.assertEqual(result['logical_nets_created'],0)
        bad = copy.deepcopy(p)
        bad['cells'][lc][0][2] = bad['cells'][lc][1][2]
        with self.assertRaisesRegex(ValueError,'bijective'):
            decode('lut_topology',bad,payload)

    def options(self,target='5M80ZE64C5'):
        p, _ = models.load(target,'io_options')
        raw = bytearray(p['cfm_bits']//8)
        for field in p['fields']:set_bit(raw,field['offset'],1-field['active_raw'])
        for offset,value in p['signature']:set_bit(raw,offset,value)
        return p,raw

    def test_io_qualified_qsf_uses_existing_exact_pin(self):
        p,raw = self.options()
        for field in p['fields']:
            if field['kind']=='ioe_slow_slew_bit':set_bit(raw,field['offset'],field['active_raw'])
        result = decode('io_options',p,raw)
        self.assertEqual(qsf_lines(result,p,[{'pin':'64','mode':'push_pull'}]),['set_instance_assignment -name SLOW_SLEW_RATE ON -to p_64\n'])
        self.assertEqual(qsf_lines(result,p,[{'pin':'6','mode':'push_pull'}]),[])
        result['target']='5M80ZE64C4'
        with self.assertRaisesRegex(ValueError,'target/site'):qsf_lines(result,p,[])

    def test_io_conflicts_and_partial_group_rejected(self):
        p,raw = self.options()
        group=[s for s in p['fields'] if s['kind']=='ioe_current_strength_8ma_group_bit']
        set_bit(raw,group[0]['offset'],group[0]['active_raw'])
        result = decode('io_options',p,raw)
        self.assertIn('current_strength_group_bits_disagree',result['blockers'])
        with self.assertRaisesRegex(ValueError,'blocked'):qsf_lines(result,p,[{'pin':'64','mode':'push_pull'}])
        for s in group:set_bit(raw,s['offset'],1-s['active_raw'])
        for s in p['fields']:
            if s['kind'] in ('ioe_bus_hold_bit','ioe_weak_pull_up_bit'):set_bit(raw,s['offset'],s['active_raw'])
        result=decode('io_options',p,raw)
        self.assertIn('bus_hold_conflicts_with_weak_pull_up',result['blockers'])
        with self.assertRaisesRegex(ValueError,'blocked'):qsf_lines(result,p,[{'pin':'64','mode':'push_pull'}])

    def test_io_scope_and_output_signature(self):
        p,raw = self.options('5M40ZE64C5')
        self.assertFalse(decode('io_options',p,raw)['qsf_fragment_allowed'])
        self.assertEqual(qsf_lines(decode('io_options',p,raw),p,[{'pin':'64','mode':'push_pull'}]),[])
        p,raw = self.options('5M1270ZT144C5')
        set_bit(raw,p['signature'][0][0],0)
        result=decode('io_options',p,raw)
        self.assertEqual(result['status'],'not_applicable_exact_site')
        result['site_signature_matches']=True
        with self.assertRaisesRegex(ValueError,'signature'):
            qsf_lines(result,p,[{'pin':'32','mode':'push_pull'}])
        set_bit(raw,p['signature'][0][0],1)
        result=decode('io_options',p,raw)
        with self.assertRaisesRegex(ValueError,'output port'):qsf_lines(result,p,[{'pin':'32','mode':'released'}])

    def test_blocked_bound_project_writes_nothing(self):
        import json
        from maxvell.examples import demo_functional
        from maxvell.project import emit
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            demo_functional(root/'demo')
            model=json.loads((root/'demo/functional_ir.json').read_text())
            model['io_options']['target']='5M80ZE64C5'
            with self.assertRaisesRegex(ValueError,'target/site'):
                emit(model,root/'invalid',bind_pins=True)
            self.assertFalse((root/'invalid').exists())

    def test_fresh_pof_io_option_reaches_bound_project(self):
        from maxvell.examples import demo_functional
        from maxvell.decode import inspect
        from maxvell.functional import reconstruct
        from maxvell.project import emit
        from test_tools import pof_bytes
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            demo_functional(root/'demo')
            pof,_=inspect(root/'demo/synthetic.pof')
            payload=bytearray(pof.section_payload(17))
            provider,_=models.load('5M80ZE64C5','io_options')
            for field in provider['fields']:
                value=field['active_raw'] if field['kind']=='ioe_weak_pull_up_bit' else 1-field['active_raw']
                set_bit(payload,field['offset'],value)
            path=root/'own.pof'
            path.write_bytes(pof_bytes('5M80ZE64C5',payload))
            model=reconstruct(path)
            emit(model,root/'bound',bind_pins=True)
            self.assertIn('set_instance_assignment -name WEAK_PULL_UP_RESISTOR ON -to p_64',
                          (root/'bound/recovered.qsf').read_text())

    def test_excluded_io_conflict_does_not_block_selected_output(self):
        from maxvell.examples import demo_functional
        from maxvell.decode import inspect
        from maxvell.functional import reconstruct
        from maxvell.project import emit
        from test_tools import pof_bytes
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            demo_functional(root/'demo')
            pof,_=inspect(root/'demo/synthetic.pof')
            payload=bytearray(pof.section_payload(17))
            provider,_=models.load('5M80ZE64C5','io_options')
            for field in provider['fields']:
                active=field['kind'] in ('ioe_bus_hold_bit','ioe_weak_pull_up_bit')
                set_bit(payload,field['offset'],field['active_raw'] if active else 1-field['active_raw'])
            path=root/'own.pof'
            path.write_bytes(pof_bytes('5M80ZE64C5',payload))
            full=reconstruct(path)
            self.assertIn('64',[p['pin'] for p in full['pins']])
            with self.assertRaisesRegex(ValueError,'blocked'):
                emit(full,root/'invalid',bind_pins=True)
            self.assertFalse((root/'invalid').exists())
            selected=reconstruct(path,['4'])
            self.assertNotIn('64',[p['pin'] for p in selected['pins']])
            self.assertIn('bus_hold_conflicts_with_weak_pull_up',selected['io_options']['blockers'])
            emit(selected,root/'selected',bind_pins=True)
            import json
            manifest=json.loads((root/'selected/manifest.json').read_text())
            self.assertEqual(manifest['io_option_assignments_applied'],0)
            qsf=(root/'selected/recovered.qsf').read_text()
            self.assertIn('set_location_assignment PIN_4 -to p_4',qsf)
            self.assertNotIn('-to p_64',qsf)

    def test_released_pin_omits_output_options_but_keeps_input_options(self):
        from maxvell.examples import demo_functional
        from maxvell.decode import inspect
        from maxvell.functional import reconstruct
        from maxvell.project import emit
        from test_tools import pof_bytes
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            demo_functional(root/'demo')
            pof,_=inspect(root/'demo/synthetic.pof')
            payload=bytearray(pof.section_payload(17))
            provider,_=models.load('5M80ZE64C5','io_options')
            for field in provider['fields']:
                active=field['kind'] in ('ioe_current_strength_8ma_group_bit','ioe_slow_slew_bit','ioe_weak_pull_up_bit')
                set_bit(payload,field['offset'],field['active_raw'] if active else 1-field['active_raw'])
            # This own demo's p_64 OE inversion bit releases the otherwise modeled pad.
            set_bit(payload,572,1-((payload[572//8]>>(572%8))&1))
            path=root/'own.pof'
            path.write_bytes(pof_bytes('5M80ZE64C5',payload))
            model=reconstruct(path)
            pin=next(p for p in model['pins'] if p['pin']=='64')
            self.assertEqual(pin['mode'],'push_pull')
            self.assertEqual(pin['oe'],{'kind':'constant','value':0})
            emit(model,root/'bound',bind_pins=True)
            qsf=(root/'bound/recovered.qsf').read_text()
            self.assertIn('WEAK_PULL_UP_RESISTOR ON -to p_64',qsf)
            self.assertNotIn('CURRENT_STRENGTH_NEW',qsf)
            self.assertNotIn('SLOW_SLEW_RATE',qsf)
            options=decode('io_options',provider,payload)
            self.assertEqual(qsf_lines(options,provider,[{'pin':'64','mode':'open_drain','data':{'kind':'constant','value':1},'oe':{'kind':'constant','value':1}}]),
                             ['set_instance_assignment -name WEAK_PULL_UP_RESISTOR ON -to p_64\n'])

    def test_retained_topology_cell_emission_is_explicitly_partial(self):
        from maxvell.emit import emit_lut
        for target,count in [('5M570ZT144C5',570),('5M2210ZF324C5',2210)]:
            provider,_=models.load(target,'lut_topology')
            payload=bytearray(provider['cfm_bits']//8)
            lc=sorted(provider['cells'])[0]
            offset,physical,semantic=provider['cells'][lc][0]
            set_bit(payload,offset,1)
            data=decode('lut_topology',provider,payload)
            self.assertEqual(len(data['cells']),count)
            ir={'format':'maxvell.storage_ir.v1','target':target,'productive_emission_allowed':False,'stages':{'lut_topology':data}}
            with tempfile.TemporaryDirectory() as temp:
                out=Path(temp)/'project'
                result=emit_lut(ir,out,lc,view='retained-topology')
                self.assertEqual(result['truth_view'],'retained-topology')
                self.assertFalse(result['productive_emission_allowed'])
                self.assertIn(f"16'h{1 << semantic:04X}",(out/'cells.v').read_text())
                with self.assertRaisesRegex(ValueError,'logical-minterm'):
                    emit_lut(ir,Path(temp)/'unqualified',lc)
