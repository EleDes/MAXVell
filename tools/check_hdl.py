"""Check emitted example HDL with a user-supplied Questa/ModelSim installation."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from maxvell.project import emit
from maxvell.simulation import simulate

def testbench(model):
    inputs={p:0 for p in model['inputs']};inputs['e']=1
    steps=[];current=dict(inputs)
    # Each event changes one independent input. Include hold, load-data tracking,
    # clear-over-load, clear release, and the subsequent selected clock edge.
    for pin,value in [('c',1),('c',0),('c',1),('c',0),('e',0),('c',1),('c',0),('e',1),('l',1),('d',1),('rst',1),('d',0),('rst',0),('l',0),('c',1)]:
        current={**current,pin:value};steps.append(current)
    lc=next(iter(model['registers']))
    stimulus={'initial_inputs':inputs,'initial_state':{lc:0},'boundary_values':{},'input_steps':steps}
    expected=[r['state'][lc] for r in simulate(model,stimulus)['steps']]
    lines=['`timescale 1ns/1ps','module tb;']
    lines += [f"reg {pin}={value};" for pin,value in inputs.items()]
    lines += [f'wire p_{pin}; assign p_{pin}={pin};' for pin in inputs]
    lines += ['wire q;','recovered dut('+','.join([f'.p_{pin}(p_{pin})' for pin in inputs]+['.p_q(q)'])+');','initial begin',"#1; rst=1; #10; rst=0; #10;"]
    before=inputs
    for index,(after,value) in enumerate(zip(steps,expected)):
        pin=next(p for p in after if after[p]!=before[p])
        lines += [f'{pin}={after[pin]}; #10;',f"if(q !== 1'b{value}) $fatal(1, \"step {index}: expected {value}, actual %b\",q);"]
        before=after
    lines += [f'$display("MAXVELL_HDL_PASS steps={len(steps)}");','$finish;','end','endmodule','']
    return '\n'.join(lines),stimulus,len(steps)

def check(simulator_dir,maxv_atoms,out):
    simulator_dir=simulator_dir.resolve();maxv_atoms=maxv_atoms.resolve();out=out.resolve()
    if not maxv_atoms.is_file():raise ValueError('Supply the installed maxv_atoms.v file')
    binaries={name:simulator_dir/(name+('.exe' if (simulator_dir/(name+'.exe')).is_file() else '')) for name in ('vlib','vlog','vsim')}
    if any(not p.is_file() for p in binaries.values()):raise ValueError('Simulator directory must contain vlib, vlog and vsim')
    if out.exists() and (not out.is_dir() or any(out.iterdir())):raise ValueError('HDL check directory must be empty')
    model=json.loads((ROOT/'examples/feedback_model.json').read_text(encoding='utf-8'))
    bench,stimulus,steps=testbench(model)
    emit(model,out)
    (out/'tb.sv').write_text(bench,encoding='ascii',newline='\n')
    (out/'stimulus.json').write_text(json.dumps(stimulus,indent=2)+'\n',encoding='utf-8')
    commands=[('library',[str(binaries['vlib']),'work']),
              ('compile',[str(binaries['vlog']),'-quiet','-work','work',str(maxv_atoms),'recovered.v']),
              ('testbench',[str(binaries['vlog']),'-quiet','-sv','-work','work','tb.sv']),
              ('simulate',[str(binaries['vsim']),'-c','-quiet','-onfinish','stop','work.tb','-do','onerror {quit -code 1}; run -all; quit -f'])]
    warnings={}
    for phase,args in commands:
        try:result=subprocess.run(args,cwd=out,capture_output=True,text=True,timeout=60)
        except subprocess.TimeoutExpired as error:
            raise ValueError(f'{phase} exceeded 60 seconds') from error
        log=result.stdout+result.stderr;(out/(phase+'.log')).write_text(log,encoding='utf-8')
        warnings[phase]=len(re.findall(r'\*\* Warning',log))
        if result.returncode or warnings[phase] or re.search(r'\*\* (?:Error|Fatal)',log) or (phase=='simulate' and 'MAXVELL_HDL_PASS' not in log):
            raise ValueError(f'{phase} failed; inspect {phase}.log in the output directory')
    report={'format':'maxvell.hdl_example_check.v1','status':'passed','steps':steps,
            'warnings':warnings,
            'vendor_model_sha256':hashlib.sha256(maxv_atoms.read_bytes()).hexdigest(),
            'scope':'Emitted own feedback/control example; settled binary events after explicit reset',
            'quartus_compile_verified':False,'whole_input_equivalence_verified':False,'hardware_verified':False}
    (out/'hdl_check.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--simulator-dir',type=Path,required=True);parser.add_argument('--maxv-atoms',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    try:print(json.dumps(check(args.simulator_dir,args.maxv_atoms,args.out),sort_keys=True))
    except (ValueError,OSError,subprocess.SubprocessError) as error:print(str(error),file=sys.stderr);raise SystemExit(1)
