import contextlib
import subprocess
import json
import sys
from functools import cached_property, cache
from pywayland.client import Display
from pywayland.protocol.wayland import WlRegistry, WlSeat, WlPointer
import libevdev

from caravan import zwlr_virtual_pointer_manager_v1
from caravan.zwlr_virtual_pointer_v1 import ZwlrVirtualPointerV1Proxy


class Pointer:
    wl_pointer: WlPointer
    pointer_manager: zwlr_virtual_pointer_manager_v1.ZwlrVirtualPointerManagerV1Proxy
    seat: WlSeat

    def __init__(self, display: Display):
        self.display = display

    def handle_registry_global(self, registry: WlRegistry, id_num: int, interface: str, version: int) -> None:
        if interface == 'zwlr_virtual_pointer_manager_v1':
            self.pointer_manager = registry.bind(
                id_num, zwlr_virtual_pointer_manager_v1.ZwlrVirtualPointerManagerV1, version
            )
        elif interface == 'wl_seat':
            self.seat = registry.bind(id_num, WlSeat, version)

    @cached_property
    def wl_pointer(self) -> ZwlrVirtualPointerV1Proxy:
        assert self.pointer_manager
        assert self.seat
        return self.pointer_manager.create_virtual_pointer(self.seat)

    @cached_property
    def res_factor(self):
        cur = get_current_output()
        return (cur['rect']['width'] / 1920, cur['rect']['height'] / 1080)

    @cached_property
    def scale_factor(self):
        cur = get_current_output()
        return cur['scale']

    def move(self, x, y, real_coords=False):
        xr, yr = self.res_factor
        if not real_coords:
            x *= xr
            y *= yr
        else:
            x = int(x / self.scale_factor)
            y = int(y / self.scale_factor)
        self.wl_pointer.motion_absolute(0, int(x), int(y), int(1920 * xr), int(1080 * yr))
        self.wl_pointer.frame()
        self.display.roundtrip()

    def click(self, button='BTN_LEFT'):
        code = libevdev.evbit('EV_KEY', button)
        self.wl_pointer.button(0, code, WlPointer.button_state.pressed)
        self.wl_pointer.frame()
        self.display.roundtrip()
        self.wl_pointer.button(0, code, WlPointer.button_state.released)
        self.wl_pointer.frame()
        self.display.roundtrip()

    def wheel(self, value):
        self.wl_pointer.axis(0, WlPointer.axis.vertical_scroll, value)
        self.wl_pointer.axis_source(WlPointer.axis_source.wheel)
        self.wl_pointer.frame()
        self.display.roundtrip()


@contextlib.contextmanager
def virtual_pointer():
    with Display() as display:
        pointer = Pointer(display)

        registry = display.get_registry()
        registry.dispatcher["global"] = pointer.handle_registry_global

        display.dispatch(block=True)
        display.roundtrip()

        if not pointer.pointer_manager:
            sys.exit('zwlr_virtual_pointer_manager_v1 not supported by compositor')
        assert pointer.seat

        yield pointer


@cache
def get_current_output():
    outs = subprocess.check_output(['swaymsg', '-t', 'get_outputs'])
    return next(o for o in json.loads(outs) if o['active'])


def main():
    with virtual_pointer() as pointer:
        pointer.move(5, 1065)
        pointer.click()
        # pointer.wheel(-60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
