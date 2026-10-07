import subprocess

ADB = r"C:\Users\rafique_\AppData\Local\Android\Sdk\platform-tools\adb.exe"
DEV = "adb-083672527L002160-j80YDT._adb-tls-connect._tcp"

def main():
    subprocess.run([ADB, "-s", DEV, "shell", "run-as com.eykon.memory mkdir -p databases"], check=True)
    for fname in ["memories.db", "memories.db-wal", "memories.db-shm"]:
        with open(f"scratch/{fname}", "rb") as f:
            data = f.read()
        subprocess.run([ADB, "-s", DEV, "shell", f"run-as com.eykon.memory sh -c 'cat > databases/{fname}'"], input=data, check=True)
        print(f"Piped {fname} ({len(data)} bytes) to Infinix")
    
    out = subprocess.check_output([ADB, "-s", DEV, "shell", "run-as com.eykon.memory ls -la databases/"], text=True)
    print("Databases list:")
    print(out)

if __name__ == "__main__":
    main()
