import contextlib
import sys
from functools import cached_property
from pywayland.client import Display
from pywayland.protocol.wayland import WlRegistry, WlSeat, WlPointer, WlOutput
import libevdev

from caravan import zwlr_virtual_pointer_manager_v1
from caravan.zwlr_virtual_pointer_v1 import ZwlrVirtualPointerV1Proxy
from caravan.zxdg_output_manager_v1 import ZxdgOutputManagerV1, ZxdgOutputManagerV1Proxy


class Output:
    def __init__(self, id_num, proxy):
        self.id_num = id_num
        self.proxy = proxy
        self.x = None
        self.y = None
        self.width = 0
        self.height = 0
        self.scale = 0.0
        self.current = False

    def handle_mode(self, proxy, flags, width, height, refresh):
        self.width = width
        self.height = height
        if flags & WlOutput.mode.current:
            self.current = True

    def handle_scale(self, proxy, factor):
        self.scale = factor

    def handle_logical_position(self, proxy, x, y):
        self.x = x
        self.y = y


class Pointer:
    wl_pointer: WlPointer
    pointer_manager: zwlr_virtual_pointer_manager_v1.ZwlrVirtualPointerManagerV1Proxy
    seat: WlSeat
    xdg_output_manager: ZxdgOutputManagerV1Proxy

    def __init__(self, display: Display):
        self.display = display
        self.outputs = []

    def handle_registry_global(self, registry: WlRegistry, id_num: int, interface: str, version: int) -> None:
        if interface == 'zwlr_virtual_pointer_manager_v1':
            self.pointer_manager = registry.bind(
                id_num, zwlr_virtual_pointer_manager_v1.ZwlrVirtualPointerManagerV1, version
            )
        elif interface == 'wl_seat':
            self.seat = registry.bind(id_num, WlSeat, version)
        elif interface == 'wl_output':
            wl_output = registry.bind(id_num, WlOutput, version)
            output = Output(id_num, wl_output)
            wl_output.dispatcher['mode'] = output.handle_mode
            wl_output.dispatcher['scale'] = output.handle_scale
            self.outputs.append(output)
        elif interface == 'zxdg_output_manager_v1':
            self.xdg_output_manager = registry.bind(id_num, ZxdgOutputManagerV1, version)

    def get_xdg_outputs(self):
        for output in self.outputs:
            xdg_output = self.xdg_output_manager.get_xdg_output(output.proxy)
            xdg_output.dispatcher['logical_position'] = output.handle_logical_position

    @cached_property
    def wl_pointer(self) -> ZwlrVirtualPointerV1Proxy:
        assert self.pointer_manager
        assert self.seat
        return self.pointer_manager.create_virtual_pointer(self.seat)

    @cached_property
    def current_output(self) -> Output:
        return next(o for o in self.outputs if o.current)

    @cached_property
    def res_factor(self):
        return (self.current_output.width / 1920, self.current_output.height / 1080)

    @cached_property
    def scale_factor(self):
        assert self.current_output.scale
        return self.current_output.scale

    def move(self, x, y, real_coords=False):
        xr, yr = self.res_factor
        if not real_coords:
            x *= xr
            y *= yr
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
        if not pointer.xdg_output_manager:
            sys.exit('zxdg_output_manager_v1 not supported by compositor')
        assert pointer.seat

        pointer.get_xdg_outputs()
        display.roundtrip()

        yield pointer


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
