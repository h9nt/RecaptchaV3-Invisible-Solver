from requests import Session
import re
from pyproto import ProtoBuf
from colorama import Fore
import base64
import time
import random
import json


def generate_human_mouse_path(
    start_x: int = 400,
    start_y: int = 300,
    end_x: int = 1200,
    end_y: int = 700,
    steps: int = 12,
    noise: float = 0.8,
    speed_factor: float = 1.0,
) -> list:
    path = []
    current_x = start_x
    current_y = start_y
    base_time = int(time.time() * 1000)

    for i in range(steps):
        t = i / (steps - 1)  # 0 → 1
        eased_t = t * t * (3 - 2 * t)

        target_x = start_x + (end_x - start_x) * eased_t
        target_y = start_y + (end_y - start_y) * eased_t
        noise_x = random.gauss(0, 12 * noise * (1 - eased_t))
        noise_y = random.gauss(0, 12 * noise * (1 - eased_t))

        current_x += (target_x - current_x + noise_x) * 0.6
        current_y += (target_y - current_y + noise_y) * 0.6

        delay = random.randint(40, 140) * speed_factor
        if i == 0 or i == steps - 1:
            delay += random.randint(80, 250)

        base_time += delay

        path.append([1, round(current_x), round(current_y), base_time])

    return path


def generate_realistic_telemetry():
    ts_base = int(time.time() * 1000) - random.randint(8000, 25000)
    mouse_paths = []
    for _ in range(random.randint(2, 4)):
        start_x = random.randint(200, 1400)
        start_y = random.randint(150, 800)
        end_x = random.randint(400, 1600)
        end_y = random.randint(300, 900)
        path = generate_human_mouse_path(start_x, start_y, end_x, end_y)
        mouse_paths.extend(path)

    scroll_events = [
        [2, random.randint(40, 120), ts_base + random.randint(500, 3000)],
        [2, random.randint(50, 180), ts_base + random.randint(2000, 6000)],
        [2, random.randint(60, 220), ts_base + random.randint(4000, 9000)],
    ]

    metrics = [
        None,
        None,
        None,
        [
            9,
            round(random.uniform(5, 12), 8),
            round(random.uniform(0.005, 0.03), 8),
            random.randint(12, 24),
        ],
        [
            random.randint(80, 140),
            round(random.uniform(0.2, 0.6), 8),
            round(random.uniform(0.003, 0.01), 8),
            random.randint(3, 8),
        ],
        0,
        0,
        0,
    ]

    domains = [
        "www.googletagmanager.com",
        "www.google.com",
        "www.gstatic.com",
        "static.cloudflareinsights.com",
        "www.googleadservices.com",
        "www.clarity.ms",
        "scripts.clarity.ms",
        "k.clarity.ms",
        "2captcha.com",
    ]

    telemetry = [
        mouse_paths,  # Maus-Events
        scroll_events,  # Scroll
        metrics,  # Visibility / Perf
        domains,  # Domains
        [random.randint(6, 12), random.randint(400, 1200)],  # Event-Count + Duration
    ]

    return telemetry


def minimal_oz_proto():
    ts_ms = int(time.time() * 1000)
    ts_b64 = base64.b64encode(str(ts_ms).encode()).decode().rstrip("=")
    oz = {
        5: str(random.randint(1000, 9999)),
        6: random.randint(1, 10),
        17: [base64.urlsafe_b64encode(random.randbytes(24)).decode().rstrip("=")],
        18: 2,
        19: ts_b64,
        28: "https://example.com/login",
        65: random.randint(1000, 5000),
        73: json.dumps(
            {
                "brands": [["Google Chrome", "120"], ["Chromium", "120"]],
                "mobile": False,
                "platform": "Windows",
            }
        ),
        74: json.dumps(
            {
                "mouse": [],
                "keyboard": [],
                "touch": [],
                "scroll": [],
                "resize": [],
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "screen": [1920, 1080],
                "timezone": 60,  # CET
                "canvas": "fake_hash",
                "webgl": "ANGLE (Intel, Intel(R) UHD Graphics, OpenGL 4.6)",
            }
        ),
    }
    oz_json = json.dumps(oz, separators=(",", ":"))
    oz_bytes = oz_json.encode("utf-8")

    return oz_bytes


def scramble(oz_bytes: bytes, timestamp_ms: int) -> str:
    z = timestamp_ms % 1000000
    m = random.randint(0, 254)

    output = [m]
    length = len(oz_bytes)
    for i, b in enumerate(oz_bytes):
        scrambled = (b + length + (z + m) * (i + m)) % 256
        output.append(scrambled)

    scrambled_bytes = bytes(output)
    b64 = base64.urlsafe_b64encode(scrambled_bytes).decode().rstrip("=")
    return "0" + b64


class RecaptchaV3:
    def __init__(self, site_key):
        self.site_key = site_key
        self.request = Session()
        self.oz = minimal_oz_proto()
        self.ts = int(time.time() * 1000)
        self.FIELD20_RAW = '[[3,174,1914],[1,406,2189]],[[2,54,605.9000000953674],[2,55,1147.9000000953674]],[null,null,null,[9,6.922222243414985,0.010676034648399429,18],[103,0.39320388580988913,0.00694027936567879,4],0,0,0],["www.googletagmanager.com","2captcha.com","static.cloudflareinsights.com","www.googleadservices.com","www.google.com","www.clarity.ms","scripts.clarity.ms","k.clarity.ms","www.gstatic.com"],[4,553]]'
        self.FIELD20_B64 = (
            base64.b64encode(self.FIELD20_RAW.encode("utf-8"))
            .decode("utf-8")
            .rstrip("=")
        )
        self.field16_value = scramble(self.oz, self.ts)
        self.anchor_url = (
            "https://www.google.com/recaptcha/api2/anchor?ar=1&k="
            + self.site_key
            + "&co=aHR0cHM6Ly8yY2FwdGNoYS5jb206NDQz&hl=de&v=gYdqkxiddE5aXrugNbBbKgtN&size=invisible&anchor-ms=20000&execute-ms=30000&cb=mh6c0yrpfypd"
        )

    def telemetry(self):
        telemetry = generate_realistic_telemetry()
        telemetry_json = json.dumps(telemetry, separators=(",", ":"))
        output = (
            base64.b64encode(telemetry_json.encode("utf-8")).decode("utf-8").rstrip("=")
        )
        return output

    def get_anchor(self):
        headers = {
            "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "x-browser-channel": "stable",
            "x-browser-year": "2026",
            "x-browser-validation": "AKIAtsVHZoiKbPixy+qSK1BgKWo=",
            "x-browser-copyright": "Copyright 2026 Google LLC. All Rights reserved.",
            "x-client-data": "COCJywE=",
            "sec-fetch-site": "cross-site",
            "sec-fetch-mode": "navigate",
            "sec-fetch-dest": "iframe",
            "sec-fetch-storage-access": "active",
            "referer": "https://2captcha.com/",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "priority": "u=0, i",
        }
        response = self.request.get(
            self.anchor_url,
            headers=headers,
        ).text
        pattern = r'id="recaptcha-token"\s+value="([^"]+)"'
        match = re.search(pattern, response)
        if match:
            # print(match.group(1))
            return match.group(1)
        else:
            return response

    def do_reload(self, anchor_token: str) -> str:
        headers = {
            "sec-ch-ua-platform": '"Windows"',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
            "content-type": "application/x-protobuffer",
            "sec-ch-ua-mobile": "?0",
            "origin": "https://www.google.com",
            "x-browser-channel": "stable",
            "x-browser-year": "2026",
            "x-browser-validation": "AKIAtsVHZoiKbPixy+qSK1BgKWo=",
            "x-browser-copyright": "Copyright 2026 Google LLC. All Rights reserved.",
            "x-client-data": "COCJywE=",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "sec-fetch-storage-access": "active",
            "referer": "https://www.google.com/recaptcha/api2/anchor?ar=1&k=6Lcyqq8oAAAAAJE7eVJ3aZp_hnJcI6LgGdYD8lge&co=aHR0cHM6Ly8yY2FwdGNoYS5jb206NDQz&hl=de&v=gYdqkxiddE5aXrugNbBbKgtN&size=invisible&anchor-ms=20000&execute-ms=30000&cb=mh6c0yrpfypd",
            "priority": "u=1, i",
        }
        data = {
            1: "gYdqkxiddE5aXrugNbBbKgtN",
            2: anchor_token,
            4: "!4uSg5OEKAAQVGigibQEHewCTCNohMqr4a80EEWyyqQ-ctfd_yZJ24quiLbO8146jEBRnqG-6pP8ss2PmRYr-Zvmer9Sp_rEyOXAsU9ZGxIAq46hbss4zcChBtFWFwOHovjuvJ0sW47q3N1HnmqdN8FKOIxswk49jHU1y5Vqc_q-dMJ-seGgBzYvXqud80XIX6apyZPBvmkFnlN6itW-bHoaKKqBQDwGO1pu0PyDH7_u1VCmMFBlH-Z6uAPF195YBwpc8x_wMIRe9oHSSkv5NnCfjPFj0MmJ2pLx_bqzZIlXydpnIuEx829KNmeqo3AsQaQCF0ykY8RYlIa68QjwhfhURPr2T4A7nzLmaNNpvYuyszExSKTnf1S-MyZ9otpnnSTkuiSxo84aSElck8ZMFKvZAD4VfGGwd94wjD3pDJyv8BY3QYPSrTAJP2X5PtFgjegNKWfAcBsQr0HIl0YNx-RhCcEOkqZio_Evsq3yaJmleu-lqELr2woW258PWwIgiio6qFhQqTlgOCHXj85SAYLXzshJ00cfIkINP0LyQ8mpwwkFhGmEqg5LFMAhLyt5kNUtv0WjfiA-ZxNo2i0HJ9zhjZZLS3j0UHwV2FXzXCjAWhDXjSpsyY4KpwPZkcABjQi2LM8zdHzp2NdzwAO0mxY6Q7KYI1Y3MO1RdHwjbDekzKaxh7Om1kSWaT2nBfA7xbTcxP23bY6rt1FstNn0UVXPw1DsRz0A65XJ7cyV5m5iijrjbm-KcAaj2IsDpbKErBtMmdZ85pydZkFHohP32dhkgMR1uHANNwjvpL6ufHPwru1_ojAYCbYucj0q4jTVrX3iOCxa5F4oOv2AGAEGcb7kLyTMMoI4y7HIX77O78UKgKG_L3ONNpPopMcyOpVnycY8ohMf-663tf2lvFXZIry4wAKC92OzEUY9dOkuIFQEbl454vmNF8XE6gqek1_k5okbMqrkAC4QFd9qHIJFT_LB2OKP_gTQeu8RJCWYZqj1-T2QUOZ4poYz_l2DDF9dIKvVtY_pYvngK0SRgWuS51Ub8RaO8BOWZysfP-cIt7j-wPT8GBhUvxRXMC9h0lXPVWgloa1R5tRCrPT6--wVjfaeZ14Mi_yAoXVBX2BCWVncwc3wG6WwJw_kNA3HHbRIHpeIuu9PVaw6uEGUf-21oZoSh1_TZSwRiXLSY898nzSD_Oo_bDvewJaBMyraZETPac6FuU_-Yt80jel4qN13KUU6-xA8felIcVnb23ln8I15GHd6BA2OMCDHZj1OffWX0CbtNMtCmcyB3kTqVHrBCJ3_RJzJAbLgYzJ3n1yv77I2L",
            5: "1776765778",
            6: "q",
            # 7:
            8: "demo_action",
            14: self.site_key,
            16: self.field16_value,
            20: base64.b64encode(
                json.dumps(generate_realistic_telemetry()).encode("utf-8")
            )
            .decode("utf-8")
            .rstrip("="),
            22: "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",
            25: "W1tbNTAwNiw5MF0sWzY0NjA3LDFdLFszNTgzNywxXV1d",
            28: random.randint(15000, 35000),
            29: random.randint(25000, 60000),
        }
        # print(data)
        response = self.request.post(
            "https://www.google.com/recaptcha/api2/reload?k=" + self.site_key,
            headers=headers,
            data=ProtoBuf(data).toBuf(),
        )
        pattern = r'"rresp"\s*,\s*"([^"]+)"'
        match = re.search(pattern, response.text)
        if match:
            token = match.group(1)
            return token
        else:
            print("No Token")

    def solve(self) -> str:
        anchor = self.get_anchor()
        if anchor:
            try:
                token = self.do_reload(anchor)
                response = self.request.post(
                    "https://2captcha.com/api/v1/captcha-demo/recaptcha/verify",
                    json={
                        "siteKey": self.site_key,
                        "answer": token,
                    },
                    headers={
                        "Host": "2captcha.com",
                        "sec-ch-ua-platform": '"Windows"',
                        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
                        "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
                        "content-type": "application/json",
                        "sec-ch-ua-mobile": "?0",
                        "accept": "*/*",
                        "origin": "https://2captcha.com",
                        "sec-fetch-site": "same-origin",
                        "sec-fetch-mode": "cors",
                        "sec-fetch-dest": "empty",
                        "referer": "https://2captcha.com/de/demo/recaptcha-v3",
                        "accept-encoding": "gzip, deflate, br, zstd",
                        "accept-language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
                        "priority": "u=1, i",
                        "Cookie": "cookie,i18next=de; cookie,guest_currency=eur; cookie,user_country=de; cookie,_gcl_au=1.1.568302645.1770520422; cookie,original_referer=https%3A%2F%2Fwww.google.com%2F; cookie,timezone=Europe%2FBerlin; cookie,first_visited_page=%2Fde%2Fdemo%2Frecaptcha-v3; cookie,last_visited_page=%2Fde%2Fdemo%2Frecaptcha-v3",
                    },
                )
                return response.json()
            except Exception as e:
                print(e)
        else:
            print("No Anchor")

    # def test(self):

    #     anchor = self.get_anchor()
    #     if anchor:
    #         try:
    #             self.do_reload(anchor)
    #         except Exception as e:
    #             print(e)
    #     else:
    #         print("No Anchor")


print(RecaptchaV3("6Lcyqq8oAAAAAJE7eVJ3aZp_hnJcI6LgGdYD8lge").solve())
