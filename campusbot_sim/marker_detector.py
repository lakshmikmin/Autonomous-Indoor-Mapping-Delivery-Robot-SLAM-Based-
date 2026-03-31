"""Color-based marker detection module for CampusBot navigation.

Uses HSV color space thresholding to detect green, red, and blue markers
in camera frames, returning navigation commands based on detected colors.
"""

from typing import Optional

import cv2
import numpy as np


class MarkerDetector:
    """Detects colored navigation markers in camera frames using HSV thresholding.

    Supports three marker colors:
        - Green → TURN_LEFT command
        - Blue  → TURN_RIGHT command
        - Red   → DESTINATION (stop) command

    Attributes:
        green_lower: Lower HSV bound for green detection.
        green_upper: Upper HSV bound for green detection.
        red_lower: Lower HSV bound for red detection.
        red_upper: Upper HSV bound for red detection.
        blue_lower: Lower HSV bound for blue detection.
        blue_upper: Upper HSV bound for blue detection.
        min_pixels: Minimum nonzero pixel count to consider a detection valid.
    """

    # Morphological kernel for noise reduction
    _MORPH_KERNEL_SIZE = 5

    def __init__(
        self,
        green_hsv_lower: list[int],
        green_hsv_upper: list[int],
        red_hsv_lower: list[int],
        red_hsv_upper: list[int],
        blue_hsv_lower: list[int],
        blue_hsv_upper: list[int],
        min_detection_pixels: int = 400,
    ) -> None:
        """Initialize the MarkerDetector with HSV threshold ranges.

        Args:
            green_hsv_lower: Lower HSV bound for green [H, S, V].
            green_hsv_upper: Upper HSV bound for green [H, S, V].
            red_hsv_lower: Lower HSV bound for red [H, S, V].
            red_hsv_upper: Upper HSV bound for red [H, S, V].
            blue_hsv_lower: Lower HSV bound for blue [H, S, V].
            blue_hsv_upper: Upper HSV bound for blue [H, S, V].
            min_detection_pixels: Minimum nonzero pixels to register a detection.
        """
        self.green_lower = np.array(green_hsv_lower, dtype=np.uint8)
        self.green_upper = np.array(green_hsv_upper, dtype=np.uint8)
        self.red_lower = np.array(red_hsv_lower, dtype=np.uint8)
        self.red_upper = np.array(red_hsv_upper, dtype=np.uint8)
        self.blue_lower = np.array(blue_hsv_lower, dtype=np.uint8)
        self.blue_upper = np.array(blue_hsv_upper, dtype=np.uint8)
        self.min_pixels = min_detection_pixels

        self._kernel = np.ones(
            (self._MORPH_KERNEL_SIZE, self._MORPH_KERNEL_SIZE), np.uint8
        )

    def _create_mask(
        self, hsv_frame: np.ndarray, lower: np.ndarray, upper: np.ndarray
    ) -> np.ndarray:
        """Create a binary mask with morphological closing applied.

        Args:
            hsv_frame: Input frame in HSV color space.
            lower: Lower HSV threshold bound.
            upper: Upper HSV threshold bound.

        Returns:
            Binary mask after thresholding and morphological closing.
        """
        mask = cv2.inRange(hsv_frame, lower, upper)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._kernel)
        return mask

    def detect(self, frame: np.ndarray) -> Optional[str]:
        """Detect the dominant colored marker in a camera frame.

        Converts the frame to HSV, applies color masks for green, red,
        and blue, and returns the navigation label for whichever color
        exceeds the minimum pixel threshold. If multiple colors exceed
        the threshold, the one with the most pixels wins.

        Args:
            frame: BGR image frame from the camera (np.ndarray).

        Returns:
            'TURN_LEFT' if green detected, 'TURN_RIGHT' if blue detected,
            'DESTINATION' if red detected, or None if no marker found.
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        green_mask = self._create_mask(hsv, self.green_lower, self.green_upper)
        red_mask = self._create_mask(hsv, self.red_lower, self.red_upper)
        blue_mask = self._create_mask(hsv, self.blue_lower, self.blue_upper)

        green_count = cv2.countNonZero(green_mask)
        red_count = cv2.countNonZero(red_mask)
        blue_count = cv2.countNonZero(blue_mask)

        # Map color → (pixel count, label)
        detections = []
        if green_count >= self.min_pixels:
            detections.append((green_count, "TURN_LEFT"))
        if red_count >= self.min_pixels:
            detections.append((red_count, "DESTINATION"))
        if blue_count >= self.min_pixels:
            detections.append((blue_count, "TURN_RIGHT"))

        if not detections:
            return None

        # Return the label with the highest pixel count
        detections.sort(key=lambda x: x[0], reverse=True)
        return detections[0][1]

    def annotate(self, frame: np.ndarray) -> np.ndarray:
        """Draw bounding boxes around detected markers on the frame.

        Args:
            frame: BGR image frame from the camera.

        Returns:
            Annotated copy of the frame with bounding boxes and labels.
        """
        annotated = frame.copy()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        color_map = {
            "GREEN (TURN_LEFT)": (
                self._create_mask(hsv, self.green_lower, self.green_upper),
                (0, 255, 0),
            ),
            "RED (DESTINATION)": (
                self._create_mask(hsv, self.red_lower, self.red_upper),
                (0, 0, 255),
            ),
            "BLUE (TURN_RIGHT)": (
                self._create_mask(hsv, self.blue_lower, self.blue_upper),
                (255, 0, 0),
            ),
        }

        for label, (mask, color) in color_map.items():
            if cv2.countNonZero(mask) < self.min_pixels:
                continue
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < self.min_pixels:
                    continue
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
                cv2.putText(
                    annotated,
                    label,
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2,
                )

        return annotated


def test_main() -> None:
    """Test entry point: create a synthetic frame and run detection."""
    # Create a test frame with a green rectangle
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Draw a green rectangle (BGR: 0, 255, 0)
    cv2.rectangle(frame, (200, 150), (400, 350), (0, 255, 0), -1)

    detector = MarkerDetector(
        green_hsv_lower=[40, 100, 100],
        green_hsv_upper=[80, 255, 255],
        red_hsv_lower=[0, 150, 100],
        red_hsv_upper=[10, 255, 255],
        blue_hsv_lower=[100, 150, 50],
        blue_hsv_upper=[130, 255, 255],
        min_detection_pixels=400,
    )

    result = detector.detect(frame)
    print(f"Detection result: {result}")
    assert result == "TURN_LEFT", f"Expected TURN_LEFT, got {result}"

    annotated = detector.annotate(frame)
    print(f"Annotated frame shape: {annotated.shape}")
    print("All tests passed!")


if __name__ == "__main__":
    test_main()
