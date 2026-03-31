"""Setup script for the campusbot_sim ROS2 package."""

import os
from glob import glob

from setuptools import find_packages, setup

package_name = "campusbot_sim"

setup(
    name=package_name,
    version="1.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (
            os.path.join("share", package_name, "worlds"),
            glob(os.path.join("worlds", "*.world")),
        ),
        (
            os.path.join("share", package_name, "launch"),
            glob(os.path.join("launch", "*launch.[pxy][yma]*")),
        ),
        (
            os.path.join("share", package_name, "config"),
            glob(os.path.join("config", "*.yaml")),
        ),
        (
            os.path.join("share", package_name, "rviz"),
            glob(os.path.join("rviz", "*.rviz")),
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="CampusBot Team",
    maintainer_email="campusbot@example.com",
    description="CampusBot corridor navigation with color marker detection",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "campusbot_navigator = campusbot_sim.navigator:main",
            "marker_detector_test = campusbot_sim.marker_detector:test_main",
        ],
    },
)
