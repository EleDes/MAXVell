"""Functional stepping of explicitly supplied models, independent of POF grants."""
from ._core.native_sequential_cone import evaluate,step

def simulate(model,stimulus):
    if model.get("format")=="maxvrec.native_partial_state_cone.v7":
        from ._core import state_control_project as project
        state=stimulus["initial_state"];before=stimulus["initial_inputs"]
        boundaries=stimulus.get("boundary_values",{})
        project.evaluate(model,before,boundaries,state)
        results=[]
        for after in stimulus["input_steps"]:
            result=project.step(model,before,after,boundaries,state)
            state=result["state"];before=after;results.append(result)
        return {"format":"maxvell.simulation.v1","steps":results,"independent_equivalence_proved":False,
            "startup_assumption":"initial_state supplied by caller","event_scope":"settled binary single-input events","boundary_assumption":"fixed caller-supplied values"}
    state=stimulus["initial_state"]
    before=stimulus["initial_inputs"]
    evaluate(model,before,state)
    results=[]
    for after in stimulus["input_steps"]:
        result=step(model,before,after,state)
        state=result["state"];before=after;results.append(result)
    return {"format":"maxvell.simulation.v1","steps":results,"independent_equivalence_proved":False,"startup_assumption":"initial_state supplied by caller"}
