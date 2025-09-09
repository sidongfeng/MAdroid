import subprocess
from enum import Enum


class ActionType(Enum):
    ACTION_UNKNOWN = 0
    NOP = 1
    ACTIVATE = 2
    BACK = 3
    CLICK = 4
    LONG_CLICK = 5
    SCROLL_TOP_DOWN = 6
    SCROLL_BOTTOM_UP = 7
    SCROLL_LEFT_RIGHT = 8
    SCROLL_RIGHT_LEFT = 9
    ACTION_DOWN = 10
    ACTION_MOVE = 11
    ACTION_UP = 12
    SCROLL = 13
    INPUT = 14


def execute_adb(adb_command):
    # print(adb_command)
    result = subprocess.run(adb_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    print(f"Command execution failed: {adb_command}")
    print(result.stderr)
    return "ERROR"


class AndroidController:

    def __init__(self, device, ip=None):
        self.device = device
        self.width, self.height = self.get_device_size()
        self.backslash = "\\"
        if ip is not None:
            self.ip = ip
        else:
            self.ip = self.get_device_ip()

    def get_device_size(self):
        adb_command = f"adb -s {self.device} shell wm size"
        result = execute_adb(adb_command)
        if result != "ERROR":
            result = result.splitlines()[-1]
            return map(int, result.split(": ")[1].split("x"))
        return 0, 0

    def get_device_ip(self):
        adb_command = f"""adb -s {self.device} shell netcfg | grep -E 'wlan0|rmnet0' | awk '{{print $3}}' | head -n 1"""
        result = execute_adb(adb_command)
        if result == "ERROR":
            raise Exception("get ip error, please set device ip manually!")
        ip = result.split("/")[0]
        print("get device {} ip success, ip is:{}".format(self.device, ip))
        return ip

    def get_activity(self):
        adb_command = "dumpsys window windows | grep -E 'mCurrentFocus'"
        result = execute_adb(adb_command)
        return result


    def back(self):
        adb_command = f"adb -s {self.device} shell input keyevent KEYCODE_BACK"
        ret = execute_adb(adb_command)
        return ret

    def tap(self, tl, br):
        x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
        adb_command = f"adb -s {self.device} shell input tap {x} {y}"
        ret = execute_adb(adb_command)
        return ret

    def tap_point(self, x: float, y: float):
        # x = int(x * self.width)
        # y = int(y * self.height)
        adb_command = f"adb -s {self.device} shell input tap {x} {y}"
        ret = execute_adb(adb_command)
        return ret

    def text(self, input_str):
        adb_command = f"adb -s {self.device} shell am broadcast -a ADB_INPUT_TEXT --es msg '{input_str}'"
        ret = execute_adb(adb_command)
        return ret

    def long_press(self, tl, br, duration=1000):
        x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
        adb_command = f"adb -s {self.device} shell input swipe {x} {y} {x} {y} {duration}"
        ret = execute_adb(adb_command)
        return ret

    def long_press_point(self, x: float, y: float, duration=1000):
        x = int(x * self.width)
        y = int(y * self.height)
        adb_command = f"adb -s {self.device} shell input swipe {x} {y} {x} {y} {duration}"
        ret = execute_adb(adb_command)
        return ret

    def swipe(self, x, y, direction, dist="short", quick=False):
        unit_dist = int(self.width / 10)
        if dist == "long":
            unit_dist *= 3
        elif dist == "medium":
            unit_dist *= 2
        # x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
        if direction == "up":
            offset = 0, -2 * unit_dist
        elif direction == "down":
            offset = 0, 2 * unit_dist
        elif direction == "left":
            offset = -1 * unit_dist, 0
        elif direction == "right":
            offset = unit_dist, 0
        else:
            return "ERROR"
        duration = 100 if quick else 400
        adb_command = f"adb -s {self.device} shell input swipe {x} {y} {x + offset[0]} {y + offset[1]} {duration}"
        ret = execute_adb(adb_command)
        return ret

    def swipe_point(self, start, end, duration=400):
        start_x, start_y = int(start[0] * self.width), int(start[1] * self.height)
        end_x, end_y = int(end[0] * self.width), int(end[1] * self.height)
        adb_command = f"adb -s {self.device} shell input swipe {start_x} {start_x} {end_x} {end_y} {duration}"
        ret = execute_adb(adb_command)
        return ret

    def execute_action(self, action_type, bounds, text=""):
        if action_type == ActionType.BACK:
            self.back()
            return
        x = (bounds[0] + bounds[2]) // 2
        y = (bounds[1] + bounds[3]) // 2
        # print("{}:({},{}):{}".format(action_type.name, x, y, text))
        if action_type == ActionType.CLICK:
            self.tap_point(x, y)
        elif action_type == ActionType.LONG_CLICK:
            self.long_press_point(x, y)
        elif action_type == ActionType.SCROLL_LEFT_RIGHT:
            self.swipe(x, y, "right")
        elif action_type == ActionType.SCROLL_RIGHT_LEFT:
            self.swipe(x, y, "left")
        elif action_type == ActionType.SCROLL_TOP_DOWN:
            self.swipe(x, y, "down")
        elif action_type == ActionType.SCROLL_BOTTOM_UP:
            self.swipe(x, y, "up")
        elif action_type == ActionType.INPUT:
            self.tap_point(x, y)
            self.text(text)


def list_all_devices():
    adb_command = "adb devices"
    device_list = []
    result = execute_adb(adb_command)
    if result != "ERROR":
        devices = result.split("\n")[1:]
        for d in devices:
            device_list.append(d.split()[0])

    return device_list


if __name__ == "__main__":
    device = list_all_devices()[0]
    print(device)
    controller = AndroidController(device)
    controller.tap([864, 2077], [1080, 2224])
