import io, json, os, ssl, sys, time, urllib.request, zipfile

BASE = r"C:\Users\86159\Documents\deepseek-harness\default-workspace\roadshow_copilot\vendor"
CTX = ssl._create_unverified_context()
PKGS = ["platformdirs", "requests", "tqdm", "urllib3", "idna", "certifi", "charset-normalizer"]


def fetch(url, tries=6):
    last = None
    for i in range(tries):
        try:
            return urllib.request.urlopen(url, timeout=60, context=CTX).read()
        except Exception as e:
            last = e
            time.sleep(2)
    raise last


def main():
    for pkg in PKGS:
        data = json.loads(fetch(f"https://pypi.org/pypi/{pkg}/json"))
        ver = data["info"]["version"]
        wheels = [u for u in data["urls"] if u["filename"].endswith(".whl")]
        pick = None
        for u in wheels:
            f = u["filename"]
            if "py3-none-any" in f:
                pick = u
                break
        if pick is None:
            pick = wheels[0]
        blob = fetch(pick["url"])
        zipfile.ZipFile(io.BytesIO(blob)).extractall(BASE)
        print(pkg, ver, pick["filename"], len(blob), flush=True)


if __name__ == "__main__":
    main()
