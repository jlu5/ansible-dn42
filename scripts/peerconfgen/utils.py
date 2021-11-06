

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
