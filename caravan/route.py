import contextlib
import sys
import os
import subprocess
import pyscreeze
from pathlib import Path

from caravan.pointer import virtual_pointer

MAX_WHEEL_SCROLLS = 10

thisdir = Path(__file__).resolve().parent


@contextlib.contextmanager
def screenshot(geom=None):
    memfd = os.memfd_create('grim', os.MFD_CLOEXEC)
    try:
        grim_args = ['grim', '-t', 'ppm']
        if geom:
            grim_args.extend(['-g', geom])
        grim_args.append('-')
        pipe = subprocess.Popen(grim_args, stdout=memfd)
        pipe.communicate()
        yield f'/proc/{os.getpid()}/fd/{memfd}'
    finally:
        os.close(memfd)


def locate(img, geom=None) -> pyscreeze.Box:
    with screenshot(geom=geom) as screen_file:
        return next(pyscreeze._locateAll_opencv(img, screen_file, step=2))


def play_alarm():
    subprocess.call(['mpv', '--quiet', '/usr/share/sounds/freedesktop/stereo/suspend-error.oga'])


def get_screenshot_geom(pointer):
    f = pointer.scale_factor
    x = int(250 * f)
    y = int(1050 * f)
    return f'0,0 {x}x{y}'


def main():
    with virtual_pointer() as pointer:
        # click "Establish Trade Route" button
        pointer.move(325, 1050)
        pointer.click()

        # move to route list
        pointer.move(420, 450)

        previous_img = str(thisdir / 'previous.png')

        geom = get_screenshot_geom(pointer)
        for _ in range(MAX_WHEEL_SCROLLS):
            try:
                box = locate(previous_img, geom=geom)
                break
            except pyscreeze.ImageNotFoundException:
                pass
            # scroll down if previous route wasn't found
            pointer.wheel(120)
        else:
            play_alarm()
            sys.exit('failed to find previous route')

        # click previous route
        pointer.move(box.left, box.top, real_coords=True)
        pointer.click()

        # click "yes" in "are you sure" dialog
        pointer.move(850, 525)
        pointer.click()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
