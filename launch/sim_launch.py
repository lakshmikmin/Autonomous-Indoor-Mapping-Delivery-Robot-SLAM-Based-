"""Launch file for CampusBot simulation.

Starts Gazebo with the campus corridor world, TurtleBot3 state publishers,
the CampusBot navigator node, and RViz2 for visualization.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """Generate the launch description for the CampusBot simulation.

    Returns:
        LaunchDescription containing all nodes and included launch files.
    """
    # Package directories
    campusbot_pkg = get_package_share_directory("campusbot_sim")
    turtlebot3_gazebo_pkg = get_package_share_directory("turtlebot3_gazebo")

    # File paths
    world_file = os.path.join(campusbot_pkg, "worlds", "campus_corridor.world")
    params_file = os.path.join(campusbot_pkg, "config", "campusbot_params.yaml")
    rviz_config = os.path.join(campusbot_pkg, "rviz", "campusbot.rviz")

    # Set TurtleBot3 model environment variable
    set_turtlebot3_model = SetEnvironmentVariable(
        name="TURTLEBOT3_MODEL", value="burger"
    )

    # Declare launch arguments
    use_sim_time = DeclareLaunchArgument(
        "use_sim_time", default_value="true", description="Use simulation clock"
    )

    # Include TurtleBot3 Gazebo launch with our custom world
    turtlebot3_gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                turtlebot3_gazebo_pkg, "launch", "turtlebot3_world.launch.py"
            )
        ),
        launch_arguments={"world": world_file}.items(),
    )

    # CampusBot navigator node
    navigator_node = Node(
        package="campusbot_sim",
        executable="campusbot_navigator",
        name="campusbot_navigator",
        output="screen",
        parameters=[params_file],
    )

    # RViz2
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config],
    )

    return LaunchDescription(
        [
            set_turtlebot3_model,
            use_sim_time,
            turtlebot3_gazebo_launch,
            navigator_node,
            rviz_node,
        ]
    )
