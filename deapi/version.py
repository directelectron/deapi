version = "5.2.dev2"
versionInfo = version.split(".")[:2]
versionInfo = list(map(int, versionInfo))
commandVersion = (versionInfo[0] - 4) * 10 + versionInfo[1]
