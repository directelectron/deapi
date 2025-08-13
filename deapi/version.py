version = "5.3.0"
versionInfo = list(map(int, version.split(".")))
commandVersion = (versionInfo[0] - 4) * 10 + versionInfo[1] + 2
print(f"DEAPI Version: {version} (Command Version: {commandVersion})")
