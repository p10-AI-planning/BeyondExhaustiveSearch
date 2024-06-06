from enum import IntEnum


class State(IntEnum):
    NONE = 0
    INIT = 1
    GOAL = 2


def convert_state_to_string(state):
    if state == State.INIT:
        return "init"
    elif state == State.GOAL:
        return "goal"
    else:
        return ""