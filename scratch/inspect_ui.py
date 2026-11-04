import sys
import subprocess
import xml.etree.ElementTree as ET

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ADB = r"C:\Users\rafique_\AppData\Local\Android\Sdk\platform-tools\adb.exe"
DEVICE = "adb-083672527L002160-j80YDT._adb-tls-connect._tcp"

def main():
    subprocess.run([ADB, "-s", DEVICE, "shell", "uiautomator", "dump", "/sdcard/uidump.xml"], check=True)
    raw = subprocess.check_output([ADB, "-s", DEVICE, "shell", "cat", "/sdcard/uidump.xml"], text=True, encoding="utf-8", errors="ignore")
    root = ET.fromstring(raw)
    for node in root.iter("node"):
        txt = node.attrib.get("text", "")
        desc = node.attrib.get("content-desc", "")
        bounds = node.attrib.get("bounds", "")
        if txt or desc:
            print(f"Node: text='{txt}' desc='{desc}' bounds={bounds}")

if __name__ == "__main__":
    main()
