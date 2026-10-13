"""Small self-contained demonstrations using own synthetic configurations."""
import base64,json,struct,zlib
from pathlib import Path
from . import models
from ._core.pof import crc16_x25
from .functional import reconstruct
from .project import emit
from .decode import write_json

def demo_functional(out):
    out=Path(out)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):raise ValueError("Demo output directory must be empty")
    fixture=json.loads((models.DATABASE.parent/'feedback_fixture.json').read_text(encoding='utf-8'))
    payload=zlib.decompress(base64.b64decode(fixture['cfm_zlib_base64'],validate=True))
    if len(payload)*8!=fixture['cfm_bits']:raise ValueError("Synthetic fixture size differs")
    header=bytearray(12);struct.pack_into('<I',header,6,len(payload)*8)
    packets=[(2,fixture['target'].encode()+b'\0'),(17,bytes(header)+payload),(8,b'\0\0')]
    data=b'POF\0'+struct.pack('<II',1,len(packets))+b''.join(struct.pack('<HI',tag,len(v))+v for tag,v in packets)
    data=data[:-2]+struct.pack('<H',crc16_x25(data[:-2]))
    out.mkdir(parents=True,exist_ok=True);path=out/'synthetic.pof';path.write_bytes(data)
    model=reconstruct(path);metrics=model['assessment']['metrics']
    if metrics['open_interfaces'] or not metrics['closed_register_models'] or not model['control_class']['register_feedback_class']['matched_cells']:
        raise ValueError("Synthetic feedback model did not close")
    write_json(out/'functional_ir.json',model);result=emit(model,out/'partial_project')
    return {'synthetic':True,'target':fixture['target'],'metrics':metrics,'project':result,'hardware_validation':False}
