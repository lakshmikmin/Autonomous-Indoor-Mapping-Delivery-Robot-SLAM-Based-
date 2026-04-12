# CampusBot - Autonomous Corridor Navigation with Color Markers
3d Fusion design - https://gmail5401024.autodesk360.com/g/shares/SH90d2dQT28d5b6028111993bc48b85bf8a6

CampusBot is a ROS2-based autonomous navigation system that guides a TurtleBot3 Burger through campus corridors using color-coded marker detection. The robot uses its onboard camera to detect green (turn), blue (turn right), and red (destination) markers, navigating a T-junction corridor to reach its goal.

Built for the **MAHE Mobility Challenge 2026**.

---

## System Requirements

| Component | Requirement |
|-----------|-------------|
| OS | Ubuntu 22.04 LTS (Jammy Jellyfish) |
| ROS2 | Humble Hawksbill |
| Python | 3.10+ |
| RAM | 8 GB minimum (Gazebo is memory-hungry) |
| GPU | Recommended for smooth Gazebo rendering |

> **Important:** This project targets Ubuntu 22.04 + ROS2 Humble specifically. It will not work on Ubuntu 20.04/Foxy or Ubuntu 24.04/Jazzy without modifications.

---

## Installation

### 1. Install ROS2 Humble (Full Desktop)

```bash
# Set locale
sudo apt update && sudo apt install locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# Add ROS2 apt repository
sudo apt install software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install curl -y
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Install ROS2 Humble Desktop
sudo apt update
sudo apt install ros-humble-desktop -y
```

### 2. Install TurtleBot3 Packages

```bash
sudo apt install ros-humble-turtlebot3* -y
```

### 3. Install Gazebo ROS Packages

```bash
sudo apt install ros-humble-gazebo-ros-pkgs -y
```

### 4. Install Nav2 (Optional)

```bash
sudo apt install ros-humble-navigation2 -y
```

### 5. Install Python Dependencies

```bash
pip install opencv-contrib-python numpy
```

### 6. Install cv_bridge and Image Transport

```bash
sudo apt install ros-humble-cv-bridge ros-humble-image-transport -y
```

---

## Environment Setup

Add the following lines to your `~/.bashrc`:

```bash
source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=burger
export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:/opt/ros/humble/share/turtlebot3_gazebo/models
```

Apply the changes:

```bash
source ~/.bashrc
```

---

## Building the Package

```bash
# Clone or copy the workspace
cd ~/campusbot_ws

# Build
colcon build --symlink-install

# Source the workspace
source install/setup.bash
```

> **Tip:** Add `source ~/campusbot_ws/install/setup.bash` to your `~/.bashrc` so you don't have to run it every time.

---

## Running the Simulation

### Option A: Everything at Once

```bash
ros2 launch campusbot_sim sim_launch.py
```

This starts Gazebo, the navigator node, and RViz2 all together.

### Option B: Separate Terminals (Better for Debugging)

**Terminal 1 — Gazebo:**
```bash
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py \
  world:=$(ros2 pkg prefix campusbot_sim)/share/campusbot_sim/worlds/campus_corridor.world
```

**Terminal 2 — Navigator Node:**
```bash
ros2 run campusbot_sim campusbot_navigator \
  --ros-args --params-file $(ros2 pkg prefix campusbot_sim)/share/campusbot_sim/config/campusbot_params.yaml
```

**Terminal 3 — Camera Feed:**
```bash
ros2 run rqt_image_view rqt_image_view /camera/image_raw
```

---

## Watching What's Happening

### View velocity commands being sent:
```bash
ros2 topic echo /cmd_vel
```

### View the camera feed:
```bash
ros2 run rqt_image_view rqt_image_view /camera/image_raw
```

### See all active topics:
```bash
ros2 topic list
```

### View the node graph:
```bash
ros2 run rqt_graph rqt_graph
```

### Check navigator logs:
```bash
ros2 topic echo /rosout --filter "name == 'campusbot_navigator'"
```

---

## Recording a Demo Video

### Using Kazam (GUI screen recorder):
```bash
sudo apt install kazam
kazam  # Click record, stop when done
```

### Using ffmpeg (command line):
```bash
ffmpeg -video_size 1920x1080 -framerate 30 -f x11grab -i :0.0 campusbot_demo.mp4
# Press Ctrl+C to stop recording
```

---

## Tuning Parameters

All parameters are in `config/campusbot_params.yaml`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `linear_speed` | 0.15 | Forward speed (m/s). Higher = faster but less time to detect markers. |
| `turn_speed` | 0.5 | Rotation speed (rad/s) during turns. |
| `detection_confidence_frames` | 3 | How many frames must agree before acting on a detection. Higher = more robust but slower to react. |
| `voting_window` | 5 | Size of the sliding window for temporal voting. |
| `turn_duration_ticks` | 95 | How many timer ticks (at 10 Hz) to sustain a turn. 95 ticks at 0.5 rad/s ≈ 90 degrees. |
| `watchdog_timeout_sec` | 10.0 | Seconds without any detection before entering recovery mode. |
| `green_hsv_lower/upper` | [40,100,100] / [80,255,255] | HSV range for green marker detection. |
| `red_hsv_lower/upper` | [0,150,100] / [10,255,255] | HSV range for red marker detection. |
| `blue_hsv_lower/upper` | [100,150,50] / [130,255,255] | HSV range for blue marker detection. |
| `min_detection_pixels` | 400 | Minimum pixels in a color mask to count as a detection. Lower = more sensitive, higher = fewer false positives. |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Gazebo doesn't open | Check `GAZEBO_MODEL_PATH` is set. Run `echo $GAZEBO_MODEL_PATH`. |
| Robot doesn't move | Run `ros2 topic echo /cmd_vel` to see if commands are being published. |
| Camera feed is empty | Run `ros2 topic list` and check `/camera/image_raw` exists. |
| TurtleBot3 model not found | Run `echo $TURTLEBOT3_MODEL` — it should say `burger`. |
| `colcon build` fails | Make sure all dependencies are installed (see Installation section). |
| Package not found after build | You forgot to run `source install/setup.bash`. |
| Markers not detected | Check lighting in Gazebo. Tune HSV ranges in the params file. Use `rqt_image_view` to see what the camera sees. |
| Robot spins forever in recovery | Increase `watchdog_timeout_sec` or check that markers are visible to the camera. |

---

## Project Architecture

```
                    +------------------+
                    |   Gazebo Sim     |
                    |  (campus world)  |
                    +--------+---------+
                             |
                   /camera/image_raw
                             |
                             v
                    +------------------+
                    |  campusbot_      |
                    |  navigator       |
                    |  (FSM + detect)  |
                    +--------+---------+
                             |
                         /cmd_vel
                             |
                             v
                    +------------------+
                    |  TurtleBot3      |
                    |  (diff drive)    |
                    +------------------+
```

**Nodes:**
- `campusbot_navigator` — subscribes to camera, publishes velocity commands
- `gazebo` — physics simulation, publishes camera images and laser scan
- `robot_state_publisher` — publishes TF transforms and robot model

**Topics:**
- `/camera/image_raw` (sensor_msgs/Image) — camera feed from TurtleBot3
- `/cmd_vel` (geometry_msgs/Twist) — velocity commands to the robot
- `/scan` (sensor_msgs/LaserScan) — LIDAR data (for visualization)

---

## What the Robot Does (Demo Walkthrough)

When you run the simulation, here's what happens:

1. **Gazebo opens** with a T-junction corridor. The TurtleBot3 Burger sits at the start of the main corridor, facing forward.

2. **The robot moves forward** at 0.15 m/s along the main corridor.

3. **Green marker #1 appears** on the right wall. The camera detects green pixels. After 3 consistent frames, the navigator confirms: "Turn left ahead."

4. **The robot slows down** (DETECTING state, 0.05 m/s) as it approaches the junction.

5. **Green marker #2 reinforces** the turn signal near the junction.

6. **The robot turns left 90 degrees** into the branch corridor (TURNING_LEFT state, rotating at 0.5 rad/s for ~9.5 seconds).

7. **After the turn completes**, the robot resumes forward motion into the branch corridor.

8. **Red marker appears** on the wall inside the branch. After 3 consistent detection frames, the navigator transitions to STOPPED.

9. **"Destination reached!"** is logged. The robot publishes zero velocity and stops.

---

## File Structure

```
campusbot_ws/
  src/
    campusbot_sim/
      campusbot_sim/
        __init__.py
        navigator.py          # Main ROS2 FSM node
        marker_detector.py    # HSV color detection module
      worlds/
        campus_corridor.world  # Gazebo SDF world file
      launch/
        sim_launch.py          # Launch file
      config/
        campusbot_params.yaml  # Tunable parameters
      rviz/
        campusbot.rviz         # RViz2 display config
      resource/
        campusbot_sim          # ament resource index marker
      package.xml              # ROS2 package manifest
      setup.py                 # Python package setup
      setup.cfg                # Install script directories
      README.md                # This file
```
