version = "5.3.0"
versionInfo = list(map(int, version.split(".")))
commandVersion = 16

# Maps each commandVersion to a representative server software version string.
# Used by FakeServer so its reported "Server Software Version" always matches
# the commandVersion used for dispatch, making tests version-agnostic.
_command_version_to_server_version = {
    16: "2.8.0.12073",
    15: "2.7.5.1000",
    13: "2.7.4.10590",
    12: "2.7.4.1000",
    11: "2.7.3.1000",
    10: "2.7.2.1000",
    4: "2.5.25.1000",
    3: "2.1.17.1000",
}

# The server version string that corresponds to the current commandVersion.
fake_server_software_version = _command_version_to_server_version.get(
    commandVersion, "2.8.0.12073"
)
