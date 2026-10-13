"""Functional behavior and scope rejection without external test artifacts."""
import copy,json,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from maxvell import models
from maxvell.coverage import coverage
from maxvell.decode import inspect,decode,decode_model
from maxvell.examples import demo_functional
from maxvell.functional import reconstruct
from maxvell.project import emit
from maxvell.simulation import simulate
from maxvell.ufm import classify,mif,emit as emit_ufm,recipe_projection
from maxvell._core.native_register_feedback_binding_v3 import binding
from maxvell._core import state_control_project as project
from maxvell._core.state_control_event import classify as event_class
from maxvell._core.pof import load_pof
from test_tools import pof_bytes

ROOT=Path(__file__).resolve().parents[1]

class FunctionalTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def example(self):return json.loads((ROOT/'examples/feedback_model.json').read_text())
    def stimulus(self):return json.loads((ROOT/'examples/feedback_stimulus.json').read_text())
    def test_real_model_pof_feedback_pipeline(self):
        result=demo_functional(self.root/'demo')
        self.assertEqual(result['metrics']['closed_register_models'],2)
        self.assertEqual(result['metrics']['closed_nonconstant_output_paths'],2)
        self.assertEqual(result['metrics']['open_interfaces'],0)
        model=json.loads((self.root/'demo/functional_ir.json').read_text())
        self.assertEqual(model['usercode'],0)
        qsf=(self.root/'demo/partial_project/recovered.qsf').read_text()
        self.assertIn('STRATIX_JTAG_USER_CODE 00000000',qsf)
        self.assertNotIn('set_location_assignment',qsf)
        self.assertIn('maxv_lcell',(self.root/'demo/partial_project/recovered.v').read_text())
        self.assertFalse(result['project']['original_equivalence_verified'])
        manifest=emit(model,self.root/'bound',bind_pins=True)
        self.assertTrue(manifest['physical_pin_assignments_applied'])
        self.assertEqual((self.root/'bound/recovered.qsf').read_text().count('set_location_assignment'),54)
    def test_feedback_events_hold_and_toggle(self):
        result=simulate(self.example(),self.stimulus());lc=next(iter(self.example()['registers']))
        self.assertEqual([r['state'][lc] for r in result['steps']],[1,1,0,0,1])
    def test_simultaneous_independent_inputs_rejected(self):
        stimulus=self.stimulus();stimulus['input_steps']=[{**stimulus['initial_inputs'],'a':1,'c':1}]
        with self.assertRaisesRegex(ValueError,'simultaneous'):simulate(self.example(),stimulus)
    def test_inconsistent_asynchronous_initial_state_rejected(self):
        stimulus=self.stimulus();lc=next(iter(stimulus['initial_state']));stimulus['initial_state'][lc]=1
        stimulus['initial_inputs']['rst']=1;stimulus['input_steps']=[stimulus['initial_inputs']]
        with self.assertRaisesRegex(ValueError,'initial'):simulate(self.example(),stimulus)
    def test_opposite_edge_state_control_settles_after_source(self):
        model=self.example();lc=next(iter(model['registers']));source='LC_X3_Y2_N0'
        leaf=copy.deepcopy(model['registers'][lc]);leaf.update(native_lc=source,clock_edge='falling',data={'kind':'constant','value':1},aclr={'kind':'constant','value':0},aload={'kind':'constant','value':0})
        leaf['qualification'].update(native_lc=source,clock_edge='falling',aclr=leaf['aclr'],aload=leaf['aload'])
        model['registers'][source]=leaf;model['registers'][lc]['aclr']={'kind':'register','native_lc':source}
        model['registers'][lc]['qualification']['aclr']=model['registers'][lc]['aclr']
        model['inputs'].remove('rst')
        self.assertEqual(len(event_class(model)['matched_controls']),1)
        before={k:v for k,v in self.stimulus()['initial_inputs'].items() if k!='rst'};before['c']=1;after={**before,'c':0}
        result=project.step(model,before,after,{},{lc:1,source:0})
        self.assertEqual(result['state'],{lc:0,source:1})
        model['registers'][source]['clock_edge']='rising'
        with self.assertRaisesRegex(ValueError,'separated'):event_class(model)
    def test_feedback_preserves_separate_async_datac(self):
        lc='LC_X1_Y1_N0'
        def scalar(kind,offset):return {'location':lc,'class':kind,'index':'none','shape':[1],'terms':[[0,0,offset,offset,0]],'sentinels':[]}
        fields=[scalar('LE_USE_REGISTER_FEEDBACK',0),scalar('LE_USE_CARRY',1)]+[{'location':lc,'class':'LE_LUT_INPUT','index':str(i)} for i in range(4)]
        ordinary={'predicted_port':'DATAC','state':'unique_source','source_resource':[7]}
        row=binding(lc,fields,b'\1',[ordinary],0x5a5a)
        self.assertEqual(row['ordinary_datac_rows'],[ordinary]);self.assertEqual(row['source_xor'],1)
        with self.assertRaisesRegex(ValueError,'arithmetic'):binding(lc,fields,b'\3',[ordinary],0x5a5a)
    def test_invalid_project_model_does_not_create_files(self):
        model=self.example();model['cells'][next(iter(model['cells']))]['mask']=65536
        with self.assertRaises(ValueError):emit(model,self.root/'out')
        self.assertFalse((self.root/'out').exists())
    def test_conceptual_pin_names_cannot_be_physically_bound(self):
        with self.assertRaisesRegex(ValueError,'Physical pin'):emit(self.example(),self.root/'bound',bind_pins=True)
        self.assertFalse((self.root/'bound').exists())
    def test_explicit_die_target_and_conflict(self):
        path=self.root/'die.pof';path.write_bytes(pof_bytes(target='5M40Z'))
        _,summary=inspect(path,'5M40ZE64C5');self.assertEqual(summary['target_binding'],'explicit_caller_target')
        with self.assertRaises(ValueError):inspect(path)
        with self.assertRaisesRegex(ValueError,'conflicts'):inspect(path,'5M80ZE64C5')
        path.write_bytes(pof_bytes())
        with self.assertRaisesRegex(ValueError,'conflicts'):inspect(path,'5M40ZE64C4')
    def test_storage_union_is_nonadditive_and_not_functional_percentage(self):
        result=coverage('5M1270ZT144C5')
        self.assertEqual(result['mapped_storage_bits']+result['unmapped_storage_bits'],208896)
        self.assertGreater(sum(result['families'].values()),result['mapped_storage_bits'])
        self.assertIsNone(result['functional_completion_percent'])
    def test_aload_candidates_are_not_promoted(self):
        provider,record=models.load('5M1270ZT144C5','aload_candidates')
        result=decode_model('5M1270ZT144C5','aload_candidates',provider,record,bytes(208896//8))
        self.assertEqual(len(result['candidate_bits']),1252)
        self.assertFalse(result['canonical_ir_allowed']);self.assertFalse(result['productive_emission_allowed'])
    def test_ufm_recipe_classification_and_draft(self):
        section=bytearray(12);struct.pack_into('<I',section,6,8192)
        path=self.root/'ufm.pof';path.write_bytes(pof_bytes(extras=[(24,bytes(section)+bytes(1024))]))
        recipe=models.load('5M40ZE64C5','ufm_recipe')[0]['recipes'][0]
        synthetic={**recipe,'recipe_key':recipe_projection(load_pof(path),recipe['signature_format'])}
        real_load=models.load
        def load(target,kind):
            if kind=='ufm_recipe':return {'recipes':[synthetic]},{}
            return real_load(target,kind)
        with patch('maxvell.ufm.models.load',side_effect=load):
            result=classify(path);self.assertEqual(result['recipe_status'],'matched_cfm_recipe')
            manifest=emit_ufm(path,self.root/'ufm_project');self.assertFalse(manifest['compile_verified'])
            bound=emit_ufm(path,self.root/'ufm_bound',bind_pins=True)
            self.assertTrue(bound['physical_pin_assignments_applied'])
            self.assertEqual((self.root/'ufm_bound/top.qsf').read_text().count('set_location_assignment'),13)
        self.assertEqual(classify(path)['recipe_status'],'unrecognized_cfm_recipe')
        with self.assertRaisesRegex(ValueError,'recipe'):emit_ufm(path,self.root/'bad')
        self.assertFalse((self.root/'bad').exists())
        self.assertIn('1FF : 0000;',mif([0]*512))
    def test_terminator_not_final_rejected(self):
        path=self.root/'bad.pof';path.write_bytes(pof_bytes(extras=[(8,b'\0\0'),(4,b'x')]))
        with self.assertRaisesRegex(ValueError,'final'):inspect(path)
    def test_bga_ufm_pin_map(self):
        from maxvell.ufm import _emit_result
        target='5M2210ZF324C5';recipe=models.load(target,'ufm_recipe')[0]['recipes'][0]
        result={'target':target,'recipe':recipe,'recipe_status':'matched_cfm_recipe','words':[0]*512}
        _emit_result(result,self.root/'bga',bind_pins=True)
        text=(self.root/'bga/top.qsf').read_text()
        self.assertIn('set_location_assignment PIN_A6 -to arclk',text)
        self.assertEqual(text.count('set_location_assignment'),13)
    def test_pin_binding_option_requires_project(self):
        from contextlib import redirect_stderr
        from io import StringIO
        from maxvell.cli import main
        for command in ('reconstruct','ufm'):
            with redirect_stderr(StringIO()),self.assertRaises(SystemExit) as error:
                main([command,'unused.pof','--out',str(self.root/'unused.json'),'--bind-pins'])
            self.assertEqual(error.exception.code,2)
        self.assertFalse((self.root/'unused.json').exists())
    def test_ufm_words_use_same_snapshot_as_recipe(self):
        section=bytearray(12);struct.pack_into('<I',section,6,8192)
        path=self.root/'changing.pof';path.write_bytes(pof_bytes(extras=[(24,bytes(section)+bytes(1024))]))
        real_inspect=inspect
        def snapshot(path,target=None):
            result=real_inspect(path,target)
            path.write_bytes(pof_bytes(extras=[(24,bytes(section)+bytes([255])*1024)]))
            return result
        with patch('maxvell.ufm.inspect',side_effect=snapshot):result=classify(path)
        self.assertEqual(result['words'],[0]*512)
    def test_ufm_content_without_cfm_can_be_exported(self):
        section=bytearray(12);struct.pack_into('<I',section,6,8192)
        packets=[(2,b'5M40ZE64C5\0'),(24,bytes(section)+bytes(1024))]
        raw=b'POF\0'+struct.pack('<II',1,len(packets))+b''.join(struct.pack('<HI',tag,len(value))+value for tag,value in packets)
        path=self.root/'content_only.pof';path.write_bytes(raw)
        result=classify(path)
        self.assertEqual(result['words'],[0]*512)
        self.assertEqual(result['recipe_status'],'no_cfm_section')
        from contextlib import redirect_stdout
        from io import StringIO
        from maxvell.cli import main
        with redirect_stdout(StringIO()):
            self.assertEqual(main(['ufm',str(path),'--out',str(self.root/'words.json'),'--mif',str(self.root/'content.mif')]),0)
        self.assertEqual(json.loads((self.root/'words.json').read_text())['words'],[0]*512)
        self.assertTrue((self.root/'content.mif').is_file())
        with self.assertRaisesRegex(ValueError,'recipe'):emit_ufm(path,self.root/'no_recipe')
        self.assertFalse((self.root/'no_recipe').exists())

if __name__=='__main__':unittest.main()
