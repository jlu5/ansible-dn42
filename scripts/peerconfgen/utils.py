import math

class FakeInput():
    """
    A mock input() function that returns a sequence of predetermined inputs,
    one for each successive input() call.
    """
    def __init__(self, inputs):
        self.inputs = inputs
        self.idx = 0
        self.max_idx = len(inputs)

    def __call__(self, _prompt):
        if self.idx < self.max_idx:
            value = self.inputs[self.idx]
            self.idx += 1
            return value
        raise ValueError("Not expecting any further input() calls")

_NO_RESPONSES = {'n', 'N', 'no', 'No', 'NO'}
_YES_RESPONSES = {'y', 'Y', 'yes', 'Yes', 'YES'}
MAX_PROMPT_TRIES = 5
def prompt_bool(prompt):
    prompt += ' [Y/N] '
    tries = 0
    while tries < MAX_PROMPT_TRIES:
        s = input(prompt).strip()
        if s in _NO_RESPONSES:
            return False
        elif s in _YES_RESPONSES:
            return True
        print(f"Invalid input: {s}")
        tries += 1
    raise ValueError("Too many failed inputs, aborting")

def prompt_float(prompt):
    tries = 0
    while tries < MAX_PROMPT_TRIES:
        s = input(prompt)
        try:
            return float(s)
        except ValueError:
            print(f"Invalid input: {s}")
            tries += 1
    raise ValueError("Too many failed inputs, aborting")

def get_iface_name(peername):
    # TODO: sanitize peer names
    return f'dn42-{peername[:10]}'

def get_dn42_latency_value(latency):
    for x in range(1, 10):
        if latency < (math.e ** x):
            return x
    return x
