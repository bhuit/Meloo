import ctypes
import struct
import pytest
from zeste.native_input import InputState, WindowsInput, RawInputHeader


def test_ctrl_sides_are_independent_and_key_repeat_not_counted():
    state=InputState()
    state.keyboard(0x11,0);state.keyboard(0x11,0);state.keyboard(0x11,2)
    assert state.down(0xA2) and state.down(0xA3) and state.ctrl_presses==2
    state.keyboard(0x11,1)
    assert not state.down(0xA2) and state.down(0xA3)
    state.keyboard(0x11,3)
    assert not state.shortcuts


def test_altgr_is_distinct_from_left_alt():
    state=InputState();state.keyboard(0x12,2)
    assert state.down(0xA5) and not state.down(0xA4)
    state.keyboard(0x12,3)
    assert not state.down(0xA5)


def test_ordinary_keys_are_never_retained():
    state=InputState()
    for key in range(0x20,0x90):state.keyboard(key,0)
    assert not state.shortcuts and state.ctrl_presses==0


@pytest.mark.parametrize('key,down,up',[(1,1,2),(2,4,8)])
def test_mouse_press_release_survives_background(key,down,up):
    state=InputState();state.mouse(down)
    assert state.down(key)
    state.mouse(0)
    assert state.down(key)
    state.mouse(up)
    assert not state.down(key) and state.mouse_presses==1


class Receiver:
    header_size=ctypes.sizeof(RawInputHeader)
    consume=WindowsInput.consume
    def __init__(self):self.state=InputState();self.mouse_messages=0;self.keyboard_messages=0


def packet(kind,payload):
    header=RawInputHeader(kind,ctypes.sizeof(RawInputHeader)+len(payload),None,1)
    return bytes(header)+payload


def test_raw_keyboard_packet_updates_ctrl_without_text():
    receiver=Receiver()
    receiver.consume(packet(1,struct.pack('<HHHH',0x1D,2,0,0x11)))
    assert receiver.state.down(0xA3)
    receiver.consume(packet(1,struct.pack('<HHHH',0x1D,3,0,0x11)))
    assert not receiver.state.down(0xA3)


def test_raw_mouse_packet_tracks_buttons_at_aligned_offset():
    receiver=Receiver()
    receiver.consume(packet(0,struct.pack('<IHH',0,1,0)))
    assert receiver.state.down(1)
    receiver.consume(packet(0,struct.pack('<IHH',0,2,0)))
    assert not receiver.state.down(1) and receiver.mouse_messages==2


def test_incomplete_or_unrelated_packets_do_not_create_inputs():
    receiver=Receiver()
    for value in [b'',b'abc',packet(1,b'\0'),packet(2,b'\xff'*20)]:receiver.consume(value)
    assert not receiver.state.shortcuts and not receiver.state.buttons
