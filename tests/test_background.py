from argparse import Namespace
import pytest
from main import open_workshop
from zeste.drag_gesture import DragGesture


def sample(gesture, **overrides):
    values = dict(pressed=True, ctrl=False, altgr=False, escape=False,
                  source_ok=True, position=(100,100), now=0., enabled=True)
    values.update(overrides)
    return gesture.update(**values)


def test_ctrl_opens_and_release_of_ctrl_keeps_wheel_until_drop():
    gesture=DragGesture()
    assert sample(gesture) is None
    assert sample(gesture,ctrl=True,position=(130,110),now=.3)=="open"
    assert sample(gesture,ctrl=False,position=(150,110),now=.4) is None
    assert gesture.opened
    assert sample(gesture,pressed=False,now=.5)=="release"
    assert not gesture.opened


@pytest.mark.parametrize("changes", [
    {"ctrl":False,"position":(150,100)},
    {"ctrl":True,"position":(100,100)},
    {"ctrl":True,"altgr":True,"position":(150,100)},
    {"ctrl":True,"position":(150,100),"enabled":False},
])
def test_no_accidental_wheel(changes):
    gesture=DragGesture();sample(gesture)
    assert sample(gesture,now=.3,**changes) is None
    assert not gesture.opened


def test_other_app_cannot_start_explorer_gesture():
    gesture=DragGesture();sample(gesture,source_ok=False)
    assert sample(gesture,ctrl=True,position=(150,100),now=.3) is None


def test_cancel_is_latched_until_next_drag():
    gesture=DragGesture();sample(gesture)
    assert sample(gesture,ctrl=True,position=(150,100),now=.3)=="open"
    assert sample(gesture,escape=True,now=.4)=="cancel"
    assert sample(gesture,ctrl=True,position=(160,100),now=.5) is None
    sample(gesture,pressed=False,now=.6)
    sample(gesture,now=1.)
    assert sample(gesture,ctrl=True,position=(150,100),now=1.3)=="open"
    assert gesture.session==2


def test_short_click_never_becomes_drag():
    gesture=DragGesture();sample(gesture,ctrl=True)
    assert sample(gesture,ctrl=True,position=(150,100),now=.05) is None
    assert sample(gesture,pressed=False,now=.08) is None


@pytest.mark.parametrize("window,files,smoke,available,expected",[
    (False,[],False,True,False),
    (True,[],False,True,True),
    (False,["photo.png"],False,True,True),
    (False,[],True,True,True),
    (False,[],False,False,True),
])
def test_start_in_tray_except_explicit_window_or_missing_tray(window,files,smoke,available,expected):
    args=Namespace(window=window,files=files,smoke=smoke,screenshot=None)
    assert open_workshop(args,available) is expected
