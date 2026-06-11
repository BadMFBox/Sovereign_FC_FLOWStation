from setuptools import setup, find_packages

setup(
    name="predator_gate",
    version="1.0.0",
    packages=find_packages(),
    py_modules=[
        "burner_main",
        "burner_state",
        "burner_ram",
        "predator_bridge",
    ],
)
