# CampusBot on Windows — Setup Guide

This guide covers running the CampusBot simulation on **Windows 10/11** using **WSL2** (Windows Subsystem for Linux).

---

## Can This Run Natively on Windows?

**Short answer: No — not fully.**

| Component | Windows Native Support | Notes |
|-----------|----------------------|-------|
| ROS2 Humble | Partial (experimental) | Builds from source only, many packages missing |
| Gazebo Classic | No | No Windows build available |
| TurtleBot3 packages | No | Depend on Gazebo |
| OpenCV / Python | Yes | Works fine natively |
| RViz2 | Partial | Requires manual build, limited |

The recommended and fully supported approach on Windows is **WSL2 + WSLg** (GUI support). This gives you a full Ubuntu 22.04 environment inside Windows with GPU-accelerated graphics — Gazebo, RViz2, and everything else works exactly like on native Linux.

---

## System Requirements

| Component | Requirement |
|-----------|-------------|
| OS | Windows 10 (build 19045+) or Windows 11 |
| RAM | 16 GB recommended (8 GB for WSL2 + 8 GB for Windows) |
| Storage | 20 GB free space for WSL2 + ROS2 + Gazebo |
| GPU | Dedicated GPU recommended (NVIDIA or AMD with WSLg driver) |
| CPU | 64-bit with virtualization support (Intel VT-x / AMD-V) |

---

## Step 1: Enable WSL2

Open **PowerShell as Administrator** and run:

```powershell
wsl --install
```

This installs WSL2 with Ubuntu by default. If you already have WSL1, upgrade:

```powershell
wsl --set-default-version 2
```

**Restart your computer** after installation.

### Verify WSL2 is running

```powershell
wsl --list --verbose
```

You should see Ubuntu with VERSION 2:

```
  NAME      STATE    VERSION
* Ubuntu    Running  2
```

---

## Step 2: Install Ubuntu 22.04 on WSL2

If `wsl --install` gave you a different Ubuntu version:

```powershell
wsl --install -d Ubuntu-22.04
```

Launch it:

```powershell
wsl -d Ubuntu-22.04
```

Set up your username and password when prompted.

### Update Ubuntu

```bash
sudo apt update && sudo apt upgrade -y
```

---

## Step 3: Enable GUI Support (WSLg)

### Windows 11

WSLg is built in — GUI apps work out of the box. No extra steps needed.

### Windows 10 (build 19045+)

WSLg support was backported. Make sure WSL is up to date:

```powershell
# Run in PowerShell (not inside WSL)
wsl --update
```

### Install GPU Drivers on Windows (Host Side)

Install the **WSL-compatible GPU driver** on your Windows host (not inside WSL):

- **NVIDIA:** Download from https://developer.nvidia.com/cuda/wsl — install the "NVIDIA GPU Driver for WSL"
- **AMD:** Use the standard Adrenalin driver (21.40.1+)
- **Intel:** Use the latest Intel Graphics driver

> **Important:** Do NOT install GPU drivers inside WSL. The WSL kernel uses the Windows host driver.

### Verify GUI works

Inside WSL2, run:

```bash
sudo apt install x11-apps -y
xclock
```

A clock window should appear on your Windows desktop. If it does, GUI support is working.

---

## Step 4: Install ROS2 Humble

Run all of these inside your WSL2 Ubuntu terminal:

```bash
# Set locale
sudo apt update && sudo apt install locales -y
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# Add ROS2 apt repository
sudo apt install software-properties-common -y
sudo add-apt-repository universe
sudo apt update && sudo apt install curl -y
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Install ROS2 Humble Desktop (includes RViz2)
sudo apt update
sudo apt install ros-humble-desktop -y
```

---

## Step 5: Install Dependencies

```bash
# TurtleBot3 packages
sudo apt install ros-humble-turtlebot3* -y

# Gazebo ROS packages
sudo apt install ros-humble-gazebo-ros-pkgs -y

# Navigation2 (optional but useful)
sudo apt install ros-humble-navigation2 -y

# cv_bridge and image transport
sudo apt install ros-humble-cv-bridge ros-humble-image-transport -y

# Python dependencies
pip install opencv-contrib-python numpy
```

---

## Step 6: Environment Setup

Add these to your `~/.bashrc` inside WSL2:

```bash
echo 'source /opt/ros/humble/setup.bash' >> ~/.bashrc
echo 'export TURTLEBOT3_MODEL=burger' >> ~/.bashrc
echo 'export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:/opt/ros/humble/share/turtlebot3_gazebo/models' >> ~/.bashrc
source ~/.bashrc
```

---

## Step 7: Copy the Project into WSL2

Your Windows drives are mounted under `/mnt/` inside WSL2. Copy the project to your WSL2 home directory for better performance:

```bash
# Copy from Windows drive to WSL2 home
cp -r /mnt/d/CampusRobot/campusbot_ws ~/campusbot_ws
```

> **Performance tip:** Always work from the WSL2 filesystem (`~/`), not from `/mnt/`. File operations on `/mnt/` (Windows drives) are significantly slower due to the 9P filesystem bridge.

---

## Step 8: Build the Package

```bash
cd ~/campusbot_ws
colcon build --symlink-install
source install/setup.bash
```

Add the workspace source to your bashrc:

```bash
echo 'source ~/campusbot_ws/install/setup.bash' >> ~/.bashrc
```

---

## Step 9: Run the Simulation

### Option A: All at once

```bash
ros2 launch campusbot_sim sim_launch.py
```

Gazebo and RViz2 windows will open on your Windows desktop via WSLg.

### Option B: Separate terminals (better for debugging)

Open multiple WSL2 terminals (you can use Windows Terminal tabs):

**Tab 1 — Gazebo:**
```bash
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py \
  world:=$(ros2 pkg prefix campusbot_sim)/share/campusbot_sim/worlds/campus_corridor.world
```

**Tab 2 — Navigator:**
```bash
ros2 run campusbot_sim campusbot_navigator \
  --ros-args --params-file $(ros2 pkg prefix campusbot_sim)/share/campusbot_sim/config/campusbot_params.yaml
```

**Tab 3 — Camera feed:**
```bash
ros2 run rqt_image_view rqt_image_view /camera/image_raw
```

---

## Step 10: Monitoring and Debugging

```bash
# See what velocity commands the robot is sending
ros2 topic echo /cmd_vel

# List all active topics
ros2 topic list

# View the node graph
ros2 run rqt_graph rqt_graph

# View camera feed
ros2 run rqt_image_view rqt_image_view /camera/image_raw
```

---

## Recording a Demo Video

### From inside WSL2:

```bash
sudo apt install ffmpeg -y
ffmpeg -video_size 1920x1080 -framerate 30 -f x11grab -i :0.0 campusbot_demo.mp4
# Press Ctrl+C to stop
```

### From Windows (recommended — easier):

Use any Windows screen recorder:
- **Xbox Game Bar:** Press `Win + G`, click Record
- **OBS Studio:** Free, works great — https://obsproject.com
- **ShareX:** Free, lightweight — https://getsharex.com

Just record the Gazebo and RViz2 windows that appear on your desktop.

---

## WSL2 Performance Tuning

### Allocate more RAM to WSL2

Create or edit `C:\Users\<YourUsername>\.wslconfig`:

```ini
[wsl2]
memory=8GB
processors=4
swap=4GB
```

Then restart WSL2:

```powershell
wsl --shutdown
wsl
```

### Enable GPU acceleration for Gazebo

Verify GPU is accessible inside WSL2:

```bash
# For NVIDIA
nvidia-smi

# For any GPU — check OpenGL
sudo apt install mesa-utils -y
glxinfo | grep "OpenGL renderer"
```

If `glxinfo` shows "llvmpipe" instead of your GPU name, the GPU driver is not working. Reinstall the Windows-side WSL GPU driver.

---

## Troubleshooting (Windows-Specific)

| Problem | Solution |
|---------|----------|
| `wsl --install` fails | Enable "Virtual Machine Platform" and "Windows Subsystem for Linux" in Windows Features (Control Panel → Programs → Turn Windows features on or off) |
| GUI apps don't open | Run `wsl --update` in PowerShell. Restart WSL with `wsl --shutdown`. |
| Gazebo is very slow / no GPU | Check GPU driver (see Performance Tuning above). Make sure you're NOT working from `/mnt/` — copy files to `~/`. |
| "Unable to open display" error | WSLg may not be running. Try `export DISPLAY=:0` inside WSL2, or restart WSL. |
| Gazebo crashes immediately | Increase WSL2 memory in `.wslconfig` to at least 6 GB. |
| `colcon build` is slow on `/mnt/` | Copy workspace to WSL2 filesystem: `cp -r /mnt/d/CampusRobot/campusbot_ws ~/campusbot_ws` |
| Network issues inside WSL2 | Try `sudo apt update` — if it fails, check your Windows firewall/VPN settings. Some VPNs block WSL2 networking. |
| Multiple Ubuntu versions confuse things | Set default: `wsl --set-default Ubuntu-22.04` |
| Permission denied errors | Don't use `sudo` for `colcon build`. If files from `/mnt/` have wrong permissions, copy them to `~/` first. |
| RViz2 renders black screen | Try `export LIBGL_ALWAYS_SOFTWARE=1` before launching (forces software rendering as a workaround). |
| Sound warnings in Gazebo | These are harmless. WSLg doesn't support audio well — ignore PulseAudio errors. |

---

## Using Windows Terminal for Multiple Tabs

Install **Windows Terminal** from the Microsoft Store if you don't have it already. It makes working with WSL2 much easier:

1. Open Windows Terminal
2. Click the dropdown arrow next to the `+` tab button
3. Select **Ubuntu-22.04**
4. Open multiple tabs for Gazebo, navigator, and monitoring

You can also split panes with `Alt+Shift+D`.

---

## Accessing WSL2 Files from Windows

Your WSL2 home directory is accessible from Windows File Explorer at:

```
\\wsl$\Ubuntu-22.04\home\<your-username>\campusbot_ws
```

You can open this in VS Code:

```powershell
code \\wsl$\Ubuntu-22.04\home\<your-username>\campusbot_ws
```

Or from inside WSL2:

```bash
cd ~/campusbot_ws
code .
```

This opens VS Code with the **Remote - WSL** extension, giving you full IDE support with the WSL2 backend.

---

## Quick Start Summary

```powershell
# 1. PowerShell (one-time setup)
wsl --install -d Ubuntu-22.04

# 2. Inside WSL2 Ubuntu (one-time setup)
# ... install ROS2, dependencies (Steps 4-6 above) ...

# 3. Copy and build
cp -r /mnt/d/CampusRobot/campusbot_ws ~/campusbot_ws
cd ~/campusbot_ws
colcon build --symlink-install
source install/setup.bash

# 4. Run
ros2 launch campusbot_sim sim_launch.py
```

That's it — Gazebo and RViz2 will open as regular Windows on your desktop.
