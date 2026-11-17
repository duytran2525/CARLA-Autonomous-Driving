"""v16 addendum N: an I-category EGO B lane change starts only after the SOURCE_CLEAR_CONFIRMED -> CHANGE transition."""
from dataclasses import replace
from fractions import Fraction as F

import pytest

GATE = {'method': 'ordered-event-program-v1', 'initial': 'NOMINAL', 'transitions': (
    {'cause': 'CHANGE', 'after_event': 'SOURCE_CLEAR_CONFIRMED', 'delay_s': F(0), 'requires': ('TRIGGER', 'LANE_CHANGE_PATH_CLEAR')},)}
# EGO pose x = 4 lies inside this moving segment, so the frozen arc profile alone asks for a non-zero offset.
PROFILE = {'method': 'quintic-arc-v1', 'segments': ({'start_arc_m': F(0), 'length_m': F(12), 'start_offset_m': F(0),
                                                    'end_offset_m': F(3)},)}


def case(category='I', action='B', events=('TRIGGER',)):
    from tests.m56.response_cases import response_case
    c = response_case(category, action, events=events, speed=4.)
    return c, replace(c.response, profile=PROFILE, phases={**c.response.phases, 'program': GATE})


def test_i_b_holds_lane_before_source_clear_instead_of_blocking(require):
    c, response = case()
    out = require('m56.response', 'step_response')(c.frame, c.state, response)
    assert out.state.phase == 'NOMINAL' and out.command.offset == 0


def test_i_b_follows_frozen_profile_once_in_change(require):
    c, response = case(events=('TRIGGER', 'SOURCE_CLEAR_CONFIRMED', 'LANE_CHANGE_PATH_CLEAR'))
    out = require('m56.response', 'step_response')(c.frame, c.state, response)
    want = require('m56.response', 'desired_offset')(F(4), response)
    assert out.state.phase == 'CHANGE' and want != 0 and out.command.offset == want


@pytest.mark.parametrize('category,action,role', [('I', 'A', 'EGO'), ('O', 'B', 'EGO'), ('I', 'B', 'NPC')])
def test_other_responses_keep_v15_offset(require, category, action, role):
    c, response = case(category, action)
    response = replace(response, actor_role=role)
    commanded = require('m56.response', 'commanded_offset')
    assert commanded(F(4), response, response, 'NOMINAL') == require('m56.response', 'desired_offset')(F(4), response)


def test_program_without_source_clear_gate_is_unchanged(require):
    from tests.m56.response_cases import response_case
    c = response_case('I', 'B', events=('TRIGGER',), speed=4.)
    response = replace(c.response, profile=PROFILE)
    commanded = require('m56.response', 'commanded_offset')
    assert commanded(F(4), response, response, 'NOMINAL') == require('m56.response', 'desired_offset')(F(4), response) != 0
