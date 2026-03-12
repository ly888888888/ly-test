"""Lightweight DSL validators and normalizers."""

def _validate_steps_list(steps):
    if not isinstance(steps, list):
        raise ValueError('Steps must be a list')
    return [validate_step(s) for s in steps]


def validate_step(step):
    if not isinstance(step, dict):
        raise ValueError('Step must be an object')
    step_type = step.get('type', 'step')
    if step_type == 'step':
        if 'case_id' in step:
            if 'api_id' in step:
                raise ValueError('step cannot have both case_id and api_id')
        else:
            for key in ['name', 'api_id', 'params']:
                if key not in step:
                    raise ValueError(f"Missing step field: {key}")
    elif step_type == 'condition':
        if 'if' not in step:
            raise ValueError('Missing condition: if')
        if 'then' not in step and 'else' not in step:
            raise ValueError('Condition must have then or else')
        if 'then' in step:
            _validate_steps_list(step['then'])
        if 'else' in step:
            _validate_steps_list(step['else'])
    elif step_type == 'loop':
        if 'times' not in step:
            raise ValueError('Missing loop times')
        if 'steps' not in step:
            raise ValueError('Missing loop steps')
        _validate_steps_list(step['steps'])
    else:
        raise ValueError(f"Unknown step type: {step_type}")
    return step


def validate_flow_steps(steps):
    return _validate_steps_list(steps)
