import hashlib
import json
import time
import random
import requests
from urllib.parse import quote
from typing import Dict, Optional

class XGorgon:
    def __init__(self, debug: bool):
        self.length = 0x14
        self.debug = debug
        self.hex_CE0 = [
            0x05, 0x00, 0x50, random.randint(0, 0xFF),
            0x47, 0x1E, 0x00, 8 * random.randint(0, 0x1F)
        ]

    def addr_BA8(self):
        hex_BA8 = list(range(256))
        tmp = 0
        for i in range(256):
            A = tmp if tmp else hex_BA8[i - 1] if i > 0 else 0
            B = self.hex_CE0[i % 8]
            if A == 0x05 and i != 1 and tmp != 0x05:
                A = 0
            C = (A + i + B) % 256
            tmp = C if C < i else 0
            hex_BA8[i], hex_BA8[C] = hex_BA8[C], hex_BA8[i]
        return hex_BA8

    def initial(self, debug, hex_BA8):
        tmp_add = []
        tmp_hex = hex_BA8.copy()
        for i in range(self.length):
            B = tmp_add[-1] if tmp_add else 0
            C = (hex_BA8[i + 1] + B) % 256
            tmp_add.append(C)
            tmp_hex[i + 1], D = tmp_hex[C], tmp_hex[i + 1]
            E = (D + D) % 256
            debug[i] ^= tmp_hex[E]
        return debug

    @staticmethod
    def reverse(num):
        return int(f"{num:02x}"[1] + f"{num:02x}"[0], 16)

    @staticmethod
    def RBIT(num):
        return int(f"{num:08b}"[::-1], 2)

    def calculate(self, debug):
        for i in range(self.length):
            B = self.reverse(debug[i])
            C = debug[(i + 1) % self.length]
            D = B ^ C
            E = self.RBIT(D)
            F = E ^ self.length
            G = (~F) & 0xFF
            debug[i] = G
        return debug

    def main(self):
        result = self.calculate(self.initial(self.debug, self.addr_BA8()))
        return f"8402{''.join(f'{x:02x}' for x in self.hex_CE0[7:8] + self.hex_CE0[3:4] + self.hex_CE0[1:2] + self.hex_CE0[6:7])}{''.join(f'{x:02x}' for x in result)}"

def getxg(param: str = "", stub: Optional[str] = None, cookie: Optional[str] = None) -> Dict[str, str]:
    gorgon = []
    current_time = int(time.time())

    url_md5 = hashlib.md5(param.encode()).hexdigest()
    gorgon.extend(int(url_md5[i:i+2], 16) for i in range(0, 8, 2))

    if stub:
        gorgon.extend(int(stub[i:i+2], 16) for i in range(0, 8, 2))
    else:
        gorgon.extend([0] * 4)

    if cookie:
        cookie_md5 = hashlib.md5(cookie.encode()).hexdigest()
        gorgon.extend(int(cookie_md5[i:i+2], 16) for i in range(0, 8, 2))
    else:
        gorgon.extend([0] * 4)

    gorgon.extend([0x0, 0x8, 0x10, 0x9])

    khronos = f"{current_time:x}"
    gorgon.extend(int(khronos[i:i+2], 16) for i in range(0, 8, 2))

    return {
        "X-Gorgon": XGorgon(gorgon).main(),
        "X-Khronos": str(current_time)
    }

def get_stub(data: Optional[Dict] = None) -> str:
    if data is None:
        return "00000000000000000000000000000000"
    return hashlib.md5(json.dumps(data).encode()).hexdigest().upper()

def getxg_m(param: str, data: Optional[str]) -> Dict[str, str]:
    return getxg(param, hashlib.md5(data.encode()).hexdigest() if data else None, None)

def make_request(url: str, method: str, headers: Dict[str, str], data: Optional[str] = None) -> requests.Response:
    session = requests.Session()
    return session.request(method, url, headers=headers, data=data)

def get_profile(session_id: str, device_id: str, iid: str, is_us: bool = False) -> str:
    parm = (f"device_id={device_id}&iid={iid}&id=kaa&version_code=34.0.0&language=en"
            f"&app_name=lite&app_version=34.0.0&carrier_region=SA&tz_offset=10800&mcc_mnc=42001"
            f"&locale=en&sys_region=SA&aid=473824&screen_width=1284&os_api=18&ac=WIFI&os_version=17.3"
            f"&app_language=en&tz_name=Asia/Riyadh&carrier_region1=SA&build_number=340002&device_platform=iphone"
            f"&device_type=iPhone13,4")
    sig = getxg_m(parm, None)
    url = f"https://{'api16-normal-quic-useast2a' if is_us else 'api16'}.tiktokv.com/aweme/v1/user/profile/self/?{parm}"
    headers = {
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": f"sessionid={session_id}",
        "sdk-version": "2",
        "user-agent": f"com.zhiliaoapp.musically/{device_id} (Linux; U; Android 5; en; {iid}; Build/PI;tt-ok/3.12.13.1)",
        "X-Gorgon": sig["X-Gorgon"],
        "X-Khronos": sig["X-Khronos"],
    }
    response = make_request(url, "GET", headers)
    return response.json()["user"]["unique_id"]

def change_username(session_id: str, device_id: str, iid: str, new_username: str, is_us: bool = False) -> str:
    data = f"unique_id={quote(new_username)}&device_id={device_id}"
    parm = (f"aid=364225&sdk_version=1012000&refresh_num=11&version_code=30.0.0&language=en-SA"
            f"&display_density=1284*2778&device_id={device_id}&channel=AppStore&click_banner=32&mcc_mnc=42001"
            f"&show_limit=0&resolution=1284*2778&aid=1233&version_name=9.1.1&os=ios&update_version_code=91115"
            f"&access=WIFI&carrier=stc&ac=WIFI&os_version=17.3&is_cold_start=0&reason=0&device_platform=iphone"
            f"&device_brand=AppleInc.&device_type=iPhone13,4")
    sig = getxg_m(parm, data)
    url = f"https://{'api16-normal-quic-useast2a' if is_us else 'api16'}.tiktokv.com/aweme/v1/commit/user/?{parm}"
    headers = {
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": f"sessionid={session_id}",
        "sdk-version": "2",
        "user-agent": f"com.zhiliaoapp.musically/{device_id} (Linux; U; Android 5; en; {iid}; Build/PI;tt-ok/3.12.13.1)",
        "X-Gorgon": sig["X-Gorgon"],
        "X-Khronos": sig["X-Khronos"],
    }
    response = make_request(url, "POST", headers, data)
    result = response.text
    return "Username change successful." if "unique_id" in result else f"Failed to change username: {result}"

def main():
    device_id = str(random.randint(777777788, 999999999999))
    iid = str(random.randint(777777788, 999999999999))
    session_id = input("Enter the sessionid: ")

    try:
        user = get_profile(session_id, device_id, iid)
        is_us = False
    except Exception:
        try:
            user = get_profile(session_id, device_id, iid, is_us=True)
            is_us = True
        except Exception:
            print("Invalid session ID or other error.")
            print("Join discord.gg/coke to get help.")
            return

    print(f"Your current TikTok username is: {user}")
    new_username = input("Enter the new username you wish to set: ")
    print(change_username(session_id, device_id, iid, new_username, is_us))
    print("discord.gg/coke")

if __name__ == "__main__":
    main()
