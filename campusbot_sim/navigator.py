"""CampusBot Navigator - Main ROS2 node for color-marker-guided corridor navigation.

Implements a finite state machine that drives a TurtleBot3 through a campus
corridor, using camera-based color marker detection to navigate turns and
identify the destination.
"""

import collections
from enum import Enum, auto
from typing import Optional

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge, CvBridgeError
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import Image

from campusbot_sim.marker_detector import MarkerDetector


class NavState(Enum):
    """Finite state machine states for the CampusBot navigator."""

    MOVING_FORWARD = auto()
    DETECTING = auto()
    TURNING_LEFT = auto()
    TURNING_RIGHT = auto()
    STOPPED = auto()
    RECOVERY = auto()


class CampusBotNavigator(Node):
    """ROS2 node that navigates a TurtleBot3 through corridors using color markers.

    Subscribes to the camera image topic, runs HSV-based marker detection,
    and publishes velocity commands based on the current FSM state.

    The node uses temporal voting (a sliding window of recent detections)
    to filter noise and only transitions states when a marker is detected
    consistently across multiple frames.

    Attributes:
        state: Current FSM state.
        bridge: CvBridge instance for ROS ↔ OpenCV conversion.
        detector: MarkerDetector instance for color-based detection.
        vote_deque: Sliding window of recent detection results.
        turn_tick_counter: Counter for tracking turn progress.
        last_detection_time: Timestamp of the last successful detection.
        status_log_counter: Counter for periodic status logging.
    """

    # Timer period in seconds (10 Hz)
    _TIMER_PERIOD_SEC = 0.1
    # Status log interval (every 20 ticks = 2 seconds at 10 Hz)
    _STATUS_LOG_INTERVAL = 20
    # Full rotation ticks for recovery (360° at 0.3 rad/s, 10 Hz)
    _RECOVERY_FULL_ROTATION_TICKS = 210

    def __init__(self) -> None:
        """Initialize the CampusBotNavigator node."""
        super().__init__("campusbot_navigator")

        # Declare parameters with defaults
        self.declare_parameter("linear_speed", 0.15)
        self.declare_parameter("turn_speed", 0.5)
        self.declare_parameter("detection_confidence_frames", 3)
        self.declare_parameter("voting_window", 5)
        self.declare_parameter("turn_duration_ticks", 95)
        self.declare_parameter("watchdog_timeout_sec", 10.0)
        self.declare_parameter("green_hsv_lower", [40, 100, 100])
        self.declare_parameter("green_hsv_upper", [80, 255, 255])
        self.declare_parameter("red_hsv_lower", [0, 150, 100])
        self.declare_parameter("red_hsv_upper", [10, 255, 255])
        self.declare_parameter("blue_hsv_lower", [100, 150, 50])
        self.declare_parameter("blue_hsv_upper", [130, 255, 255])
        self.declare_parameter("min_detection_pixels", 400)

        # Load parameters
        self.linear_speed: float = (
            self.get_parameter("linear_speed").get_parameter_value().double_value
        )
        self.turn_speed: float = (
            self.get_parameter("turn_speed").get_parameter_value().double_value
        )
        self.confidence_frames: int = (
            self.get_parameter("detection_confidence_frames")
            .get_parameter_value()
            .integer_value
        )
        self.voting_window: int = (
            self.get_parameter("voting_window").get_parameter_value().integer_value
        )
        self.turn_duration_ticks: int = (
            self.get_parameter("turn_duration_ticks")
            .get_parameter_value()
            .integer_value
        )
        self.watchdog_timeout: float = (
            self.get_parameter("watchdog_timeout_sec")
            .get_parameter_value()
            .double_value
        )
        min_pixels: int = (
            self.get_parameter("min_detection_pixels")
            .get_parameter_value()
            .integer_value
        )

        green_lower = (
            self.get_parameter("green_hsv_lower")
            .get_parameter_value()
            .integer_array_value
        )
        green_upper = (
            self.get_parameter("green_hsv_upper")
            .get_parameter_value()
            .integer_array_value
        )
        red_lower = (
            self.get_parameter("red_hsv_lower")
            .get_parameter_value()
            .integer_array_value
        )
        red_upper = (
            self.get_parameter("red_hsv_upper")
            .get_parameter_value()
            .integer_array_value
        )
        blue_lower = (
            self.get_parameter("blue_hsv_lower")
            .get_parameter_value()
            .integer_array_value
        )
        blue_upper = (
            self.get_parameter("blue_hsv_upper")
            .get_parameter_value()
            .integer_array_value
        )

        # Initialize detector
        self.detector = MarkerDetector(
            green_hsv_lower=list(green_lower),
            green_hsv_upper=list(green_upper),
            red_hsv_lower=list(red_lower),
            red_hsv_upper=list(red_upper),
            blue_hsv_lower=list(blue_lower),
            blue_hsv_upper=list(blue_upper),
            min_detection_pixels=min_pixels,
        )

        # State machine
        self.state = NavState.MOVING_FORWARD
        self.bridge = CvBridge()
        self.vote_deque: collections.deque[Optional[str]] = collections.deque(
            maxlen=self.voting_window
        )
        self.turn_tick_counter: int = 0
        self.recovery_tick_counter: int = 0
        self.last_detection_time = self.get_clock().now()
        self.status_log_counter: int = 0
        self.latest_frame: Optional[np.ndarray] = None

        # Subscriber and publisher
        self.image_sub = self.create_subscription(
            Image, "/camera/image_raw", self._image_callback, 10
        )
        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)

        # Timer for control loop (10 Hz)
        self.timer = self.create_timer(self._TIMER_PERIOD_SEC, self._control_loop)

        self.get_logger().info("CampusBotNavigator initialized. State: MOVING_FORWARD")

    def _image_callback(self, msg: Image) -> None:
        """Convert incoming ROS Image to OpenCV BGR frame.

        Args:
            msg: ROS2 sensor_msgs/Image message.
        """
        try:
            self.latest_frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except CvBridgeError as e:
            self.get_logger().error(f"CvBridge conversion failed: {e}")

    def _get_vote_winner(self) -> Optional[str]:
        """Check if any detection result has enough votes in the sliding window.

        Returns:
            The detection label if it appears >= confidence_frames times
            in the vote deque, otherwise None.
        """
        if len(self.vote_deque) < self.confidence_frames:
            return None

        counts: dict[str, int] = {}
        for vote in self.vote_deque:
            if vote is not None:
                counts[vote] = counts.get(vote, 0) + 1

        for label, count in counts.items():
            if count >= self.confidence_frames:
                return label
        return None

    def _transition_to(self, new_state: NavState) -> None:
        """Transition to a new FSM state, clearing the vote deque.

        Args:
            new_state: The target FSM state.
        """
        old_state = self.state
        self.state = new_state
        self.vote_deque.clear()
        self.get_logger().info(
            f"State transition: {old_state.name} -> {new_state.name}"
        )

    def _publish_twist(self, linear_x: float = 0.0, angular_z: float = 0.0) -> None:
        """Publish a Twist message with given linear and angular velocities.

        Args:
            linear_x: Forward velocity (m/s).
            angular_z: Rotational velocity (rad/s).
        """
        twist = Twist()
        twist.linear.x = linear_x
        twist.angular.z = angular_z
        self.cmd_pub.publish(twist)

    def _control_loop(self) -> None:
        """Main control loop callback, runs at 10 Hz.

        Executes the FSM logic: runs detection on the latest frame,
        updates the vote deque, and transitions states as needed.
        """
        # Periodic status logging (every 2 seconds)
        self.status_log_counter += 1
        if self.status_log_counter >= self._STATUS_LOG_INTERVAL:
            self.status_log_counter = 0
            self.get_logger().info(f"Current state: {self.state.name}")

        # Run detection on latest frame
        detection: Optional[str] = None
        if self.latest_frame is not None:
            detection = self.detector.detect(self.latest_frame)
            if detection is not None:
                self.get_logger().debug(f"Frame detection: {detection}")
                self.last_detection_time = self.get_clock().now()

        # FSM logic
        if self.state == NavState.STOPPED:
            self._publish_twist(0.0, 0.0)
            return

        if self.state == NavState.MOVING_FORWARD:
            self._handle_moving_forward(detection)
        elif self.state == NavState.DETECTING:
            self._handle_detecting(detection)
        elif self.state == NavState.TURNING_LEFT:
            self._handle_turning(NavState.TURNING_LEFT)
        elif self.state == NavState.TURNING_RIGHT:
            self._handle_turning(NavState.TURNING_RIGHT)
        elif self.state == NavState.RECOVERY:
            self._handle_recovery(detection)

    def _handle_moving_forward(self, detection: Optional[str]) -> None:
        """Handle MOVING_FORWARD state logic.

        Args:
            detection: Current frame detection result or None.
        """
        self._publish_twist(linear_x=self.linear_speed)
        self.vote_deque.append(detection)

        winner = self._get_vote_winner()

        if winner == "DESTINATION":
            self._transition_to(NavState.STOPPED)
            self.get_logger().info("Destination reached!")
            self._publish_twist(0.0, 0.0)
            return

        if winner == "TURN_LEFT":
            self._transition_to(NavState.DETECTING)
            self._pending_turn = NavState.TURNING_LEFT
            return

        if winner == "TURN_RIGHT":
            self._transition_to(NavState.DETECTING)
            self._pending_turn = NavState.TURNING_RIGHT
            return

        # Watchdog: no detection for too long → recovery
        elapsed = (
            self.get_clock().now() - self.last_detection_time
        ).nanoseconds / 1e9
        if elapsed > self.watchdog_timeout:
            self.get_logger().warning(
                f"No marker detected for {elapsed:.1f}s. Entering RECOVERY."
            )
            self._transition_to(NavState.RECOVERY)

    def _handle_detecting(self, detection: Optional[str]) -> None:
        """Handle DETECTING state: slow down and prepare for turn.

        Args:
            detection: Current frame detection result or None.
        """
        self._publish_twist(linear_x=0.05)

        # Check for red marker (destination) even while detecting
        self.vote_deque.append(detection)
        winner = self._get_vote_winner()
        if winner == "DESTINATION":
            self._transition_to(NavState.STOPPED)
            self.get_logger().info("Destination reached!")
            self._publish_twist(0.0, 0.0)
            return

        # Transition to the pending turn after a brief slowdown
        pending = getattr(self, "_pending_turn", NavState.TURNING_LEFT)
        self.turn_tick_counter = 0
        self._transition_to(pending)

    def _handle_turning(self, turn_state: NavState) -> None:
        """Handle TURNING_LEFT or TURNING_RIGHT state.

        Args:
            turn_state: Either NavState.TURNING_LEFT or NavState.TURNING_RIGHT.
        """
        angular = self.turn_speed if turn_state == NavState.TURNING_LEFT else -self.turn_speed
        self._publish_twist(linear_x=0.0, angular_z=angular)
        self.turn_tick_counter += 1

        if self.turn_tick_counter >= self.turn_duration_ticks:
            self.get_logger().info(
                f"Turn complete after {self.turn_tick_counter} ticks."
            )
            self.turn_tick_counter = 0
            self.last_detection_time = self.get_clock().now()
            self._transition_to(NavState.MOVING_FORWARD)

    def _handle_recovery(self, detection: Optional[str]) -> None:
        """Handle RECOVERY state: slow 360-degree rotation to find markers.

        Args:
            detection: Current frame detection result or None.
        """
        self._publish_twist(linear_x=0.0, angular_z=0.3)
        self.recovery_tick_counter += 1

        # If we detect something during recovery, go back to moving
        if detection is not None:
            self.vote_deque.append(detection)
            winner = self._get_vote_winner()
            if winner == "DESTINATION":
                self._transition_to(NavState.STOPPED)
                self.get_logger().info("Destination reached!")
                self._publish_twist(0.0, 0.0)
                return
            if winner is not None:
                self.get_logger().info(
                    f"Marker re-acquired during recovery: {winner}"
                )
                self.recovery_tick_counter = 0
                self.last_detection_time = self.get_clock().now()
                self._transition_to(NavState.MOVING_FORWARD)
                return

        # Full rotation complete without finding anything
        if self.recovery_tick_counter >= self._RECOVERY_FULL_ROTATION_TICKS:
            self.get_logger().info("Recovery rotation complete. Resuming forward.")
            self.recovery_tick_counter = 0
            self.last_detection_time = self.get_clock().now()
            self._transition_to(NavState.MOVING_FORWARD)


def main(args: list[str] | None = None) -> None:
    """Entry point for the CampusBot navigator node.

    Args:
        args: Command-line arguments passed to rclpy.init().
    """
    rclpy.init(args=args)
    node = CampusBotNavigator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down CampusBotNavigator.")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
