"""Readiness holds cover physical markers, not merely terminal target speed."""
from dataclasses import replace

from tests.m56.test_t09_complete import complete_pair


def test_ready_marker_must_hold_for_entire_half_second(complete_pair):
    # Checking only the final ready marker would incorrectly accept a transient.
    from m56.evidence import _initialization_integrity
    c=complete_pair;frames=list(c.a.raw);i=126-100;f=frames[i];e,n=f.actors
    frames[i]=replace(f,actors=(replace(e,pose=replace(e.pose,x=e.pose.x+1.)),n))
    assert _initialization_integrity(replace(c.a,raw=tuple(frames)),c.fixture)==(('INITIALIZATION_INVALID',),())
