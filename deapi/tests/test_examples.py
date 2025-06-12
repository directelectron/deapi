import importlib.util
import pathlib
import pytest
import threading


def run_python_file(file_path, timeout=60):
    file_path = pathlib.Path(file_path)
    spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
    module = importlib.util.module_from_spec(spec)

    def load_module():
        spec.loader.exec_module(module)

    thread = threading.Thread(target=load_module)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        raise TimeoutError(
            f"Loading module {file_path.name} timed out after {timeout} seconds"
        )

    return module


@pytest.mark.examples
@pytest.mark.parametrize(
    "file",
    [
        "setting_parameters/setting_up_stem.py",
        "setting_parameters/setting_up_stem.py",
        "virtual_imaging/vdf_vbf.py",
        "virtual_imaging/setting_virtual_masks.py",
        "live_imaging/taking_an_image_every_minute.py",
        "live_imaging/viewing_the_sensor.py",
        "live_imaging/viewing_the_sensor_tem.py",
        "live_imaging/bright_spot_intensity.py",
    ],
)
def test_examples(server, file):
    print(f"Running examples from port {server}")
    print(f"Example file: {file}")
    example_file = pathlib.Path(__file__).parent.parent.parent / "examples" / file
    print(f"Checking example file: {example_file}")
    print(f"Running example: {example_file.name}")
    module = run_python_file(example_file)
    assert module is not None
