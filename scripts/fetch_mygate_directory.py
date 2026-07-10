"""Pull the full MyGate resident directory for Kalpataru Radiance, all buildings.

Replays society/v3/residentinfo with the access-key captured from the app.
Saves one raw JSON per building to captures/mygate_directory/.

The access-key is a short-lived session token — re-capture from the app if you
get 401/expired. Everything else (ids) is stable.

Usage: python3 scripts/fetch_mygate_directory.py
"""
import json
import os
import time
import urllib.request

BASE = "https://app.mygate.in"
ACCESS_KEY = os.environ.get("MYGATE_ACCESS_KEY", "ZHLfVnsEijwsSNXm5Bivrd8obM24l0otcFs6PDjgkoI")
USERID = "8965039"
FLATID = "5eb58b3ac4fda21e0255222c"
SOCIETYID = "5eb58af2c4fda21e02ee8243"

OUT = os.path.join(os.path.dirname(__file__), "..", "captures", "mygate_directory")
os.makedirs(OUT, exist_ok=True)

HEADERS = {
    "access-key": ACCESS_KEY,
    "user-agent": "MyGate/1 CFNetwork/3860.600.12 Darwin/25.5.0",
    "content-type": "application/json",
    "accept": "*/*",
    "app-version": "9.29.3",
    "device-type": "O",
}


def get(path):
    req = urllib.request.Request(BASE + path, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    info = get(f"/society/v3/societyinfo?userid={USERID}&flatid={FLATID}&societyid={SOCIETYID}")
    assert info.get("es") == "0", f"societyinfo failed: {info.get('message')}"
    buildings = info["buildings"]
    print(f"{info['societyname']}: {len(buildings)} buildings")

    grand_total = 0
    for b in buildings:
        bid, bname = b["buildingid"], b["buildingname"]
        data = get(f"/society/v3/residentinfo?userid={USERID}&version=2&flatid={FLATID}&buildingid={bid}")
        if data.get("es") != "0":
            print(f"  {bname}: SKIP ({data.get('message')})")
            continue
        flats = data.get("flats") or []
        residents = sum(len(f.get("residents") or []) for f in flats)
        grand_total += residents
        fn = os.path.join(OUT, f"building_{bname.replace(' ', '_')}.json")
        with open(fn, "w") as fh:
            json.dump({"buildingid": bid, "buildingname": bname, **data}, fh, indent=2)
        print(f"  {bname}: {len(flats)} flats, {residents} residents -> {os.path.basename(fn)}")
        time.sleep(0.5)  # ponytail: be polite, not hammering their API

    print(f"TOTAL residents captured: {grand_total}")


if __name__ == "__main__":
    main()
