from quiz.street_view_collector import is_gray_image, duration_to_num_points, calculate_heading
import unittest

import pytest


class StreetViewCollectorTests(unittest.TestCase):

    def test_valid_input_values(self):
        # Arrange
        lat1 = 37
        lng1 = -122
        lat2 = 34
        lng2 = -118

        # Act
        result = calculate_heading(lat1, lng1, lat2, lng2)

        # Assert
        assert isinstance(result, float)
        assert result == 131.47569357642328

    def test_north_direction(self):
        # Arrange
        lat1 = 37.7749
        lng1 = -122.4194
        lat2 = 38.9072
        lng2 = -122.4194

        # Act
        result = calculate_heading(lat1, lng1, lat2, lng2)

        # Assert
        assert result == 0


    def test_default_image_duration_and_extra_duration(self):
        assert duration_to_num_points(10) == 50
        assert duration_to_num_points(20) == 75
        assert duration_to_num_points(0) == 25

    def test_returns_false_if_image_is_not_gray(self):
        # Arrange
        with open('./static/logo.png', 'rb') as f:
            image_data = f.read()

        # Act
        result = is_gray_image(image_data)

        # Assert
        assert result == False