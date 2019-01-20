from setuptools import setup, find_packages


with open("py_silhouette/version.py", "r") as f:
    exec(f.read())

setup(
    name="py_silhouette",
    version=__version__,
    packages=find_packages(),

    # Metadata for PyPi
    url="https://github.com/mossblaser/pysilhouette",
    author="Jonathan Heathcote",
    description="A USB driver and Python API to control the Silhouette Portrait plotter.",
    license="LGPLv3",
    classifiers=[
        "Development Status :: 3 - Alpha",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",

        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",

        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
    ],
    keywords="plotter cutter driver usb silhouette",

    # Requirements
    install_requires=["pyusb>=1.0.0", "attrs>=18.0.0"],
)
