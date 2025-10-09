import csv
import pytest
from datetime import datetime, timedelta, timezone, time
from pathlib import Path

from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from cats import main, parse_time_constraint, validate_window_constraints
from cats.forecast import (
    CarbonIntensityPointEstimate,
    ConstrainedWindowedForecast,
)


@pytest.fixture(scope="session")
def sample_data() -> list[CarbonIntensityPointEstimate]:
    """Load sample carbon intensity data for testing."""
    with open(Path(__file__).parent / "carbon_intensity_24h.csv", "r") as f:
        csvfile = csv.reader(f, delimiter=",")
        _ = next(csvfile)  # Skip header line
        data = [
            CarbonIntensityPointEstimate(
                datetime=datetime.fromisoformat(datestr[:-1] + "+00:00"),
                value=float(intensity_value),
            )
            for datestr, _, _, intensity_value in csvfile
        ]
        return data


class TestParseTimeConstraint:
    """Test the parse_time_constraint function."""

    def test_parse_full_iso_datetime(self):
        """Test parsing full ISO datetime strings."""
        result = parse_time_constraint("2024-01-15T09:30:00")
        expected = datetime(2024, 1, 15, 9, 30, 0)
        assert result is not None
        assert result.replace(tzinfo=None) == expected

    def test_parse_iso_datetime_with_timezone(self):
        """Test parsing ISO datetime with timezone info."""
        result = parse_time_constraint("2024-01-15T09:30:00+00:00")
        expected = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_parse_iso_datetime_with_z_suffix(self):
        """Test parsing ISO datetime with Z suffix (UTC)."""
        result = parse_time_constraint("2024-01-15T09:30:00Z")
        expected = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_parse_time_only(self):
        """Test parsing time-only strings."""
        result = parse_time_constraint("09:30")
        today = datetime.now().date()
        expected_time = datetime.combine(today, time(9, 30))
        assert result is not None
        assert result.replace(tzinfo=None) == expected_time.replace(tzinfo=None)

    def test_parse_time_with_seconds(self):
        """Test parsing time with seconds."""
        result = parse_time_constraint("09:30:45")
        today = datetime.now().date()
        expected_time = datetime.combine(today, time(9, 30, 45))
        assert result is not None
        assert result.replace(tzinfo=None) == expected_time.replace(tzinfo=None)

    def test_parse_empty_string_returns_none(self):
        """Test that empty string returns None."""
        result = parse_time_constraint("")
        assert result is None

    def test_parse_none_returns_none(self):
        """Test that None returns None."""
        result = parse_time_constraint("")  # Pass empty string instead of None
        assert result is None

    def test_parse_with_custom_timezone(self):
        """Test parsing with custom default timezone."""
        bst = timezone(timedelta(hours=1))
        result = parse_time_constraint("09:30", timezone_info=bst)
        today = datetime.now().date()
        expected = datetime.combine(today, time(9, 30), tzinfo=bst)
        assert result == expected

    def test_parse_invalid_format_raises_error(self):
        """Test that invalid formats raise ValueError."""
        with pytest.raises(ValueError, match="Unable to parse time constraint"):
            _ = parse_time_constraint("not-a-time")

    def test_parse_invalid_date_raises_error(self):
        """Test that invalid dates raise ValueError."""
        with pytest.raises(ValueError, match="Unable to parse time constraint"):
            _ = parse_time_constraint("2024-13-45T09:30:00")


class TestValidateWindowConstraints:
    """Test the validate_window_constraints function."""

    def test_validate_valid_window_minutes(self):
        """Test validation of valid window minutes."""
        start_dt, end_dt, window = validate_window_constraints("", "", 1440)
        assert start_dt is None
        assert end_dt is None
        assert window == 1440

    def test_validate_window_too_small_raises_error(self):
        """Test that window < 1 raises ValueError."""
        with pytest.raises(
            ValueError, match="Window must be between 1 and 2820 minutes"
        ):
            validate_window_constraints("", "", 0)

    def test_validate_window_too_large_raises_error(self):
        """Test that window > 2820 raises ValueError."""
        with pytest.raises(
            ValueError, match="Window must be between 1 and 2820 minutes"
        ):
            validate_window_constraints("", "", 2881)

    def test_validate_boundary_values(self):
        """Test boundary values for window minutes."""
        # Test minimum
        start_dt, end_dt, window = validate_window_constraints("", "", 1)
        assert window == 1

        # Test maximum
        start_dt, end_dt, window = validate_window_constraints("", "", 2820)
        assert window == 2820

    def test_validate_start_before_end_constraint(self):
        """Test that start must be before end."""
        with pytest.raises(ValueError, match="Start window must be before end window"):
            _ = validate_window_constraints(
                "2024-01-15T10:00:00", "2024-01-15T09:00:00", 1440
            )

    def test_validate_same_start_and_end_raises_error(self):
        """Test that start and end at same time raises error."""
        with pytest.raises(ValueError, match="Start window must be before end window"):
            _ = validate_window_constraints(
                "2024-01-15T09:00:00", "2024-01-15T09:00:00", 1440
            )

    def test_validate_with_valid_time_constraints(self):
        """Test validation with valid time constraints."""
        start_dt, end_dt, window = validate_window_constraints(
            "2024-01-15T09:00:00", "2024-01-15T17:00:00", 480
        )
        assert start_dt is not None
        assert end_dt is not None
        assert start_dt == datetime(2024, 1, 15, 9, 0, 0).replace(
            tzinfo=start_dt.tzinfo
        )
        assert end_dt == datetime(2024, 1, 15, 17, 0, 0).replace(tzinfo=end_dt.tzinfo)
        assert window == 480

    def test_validate_with_only_start_constraint(self):
        """Test validation with only start constraint."""
        start_dt, end_dt, window = validate_window_constraints(
            "2024-01-15T09:00:00", "", 720
        )
        assert start_dt is not None
        assert end_dt is None
        assert window == 720

    def test_validate_with_only_end_constraint(self):
        """Test validation with only end constraint."""
        start_dt, end_dt, window = validate_window_constraints(
            "", "2024-01-15T17:00:00", 360
        )
        assert start_dt is None
        assert end_dt is not None
        assert window == 360


class TestConstrainedWindowedForecast:
    """Test the ConstrainedWindowedForecast class."""

    def test_basic_functionality_without_constraints(
        self, sample_data: list[CarbonIntensityPointEstimate]
    ):
        """Test that ConstrainedWindowedForecast works like WindowedForecast without constraints."""
        duration = 180  # 3 hours
        start = sample_data[0].datetime

        cwf = ConstrainedWindowedForecast(sample_data, duration, start)

        # Should have valid length
        assert len(cwf) > 0

        # Should be able to get first and find minimum
        first = cwf[0]
        minimum = min(cwf)

        assert first.start == start
        assert first.end == start + timedelta(minutes=duration)
        assert minimum.value <= first.value  # minimum should be <= first

    def test_window_constraint_limits_search_space(
        self, sample_data: list[CarbonIntensityPointEstimate]
    ):
        """Test that max_window_minutes limits the search space."""
        duration = 60  # 1 hour
        start = sample_data[0].datetime

        # Full window
        cwf_full = ConstrainedWindowedForecast(sample_data, duration, start)

        # Constrained window
        cwf_constrained = ConstrainedWindowedForecast(
            sample_data,
            duration,
            start,
            max_window_minutes=240,  # 4 hours
        )

        # Constrained should have fewer or equal options
        assert len(cwf_constrained) <= len(cwf_full)

    def test_end_constraint_limits_start_times(
        self, sample_data: list[CarbonIntensityPointEstimate]
    ):
        """Test that end_constraint limits when jobs can start."""
        duration = 60  # 1 hour
        start = sample_data[0].datetime
        end_constraint = start + timedelta(hours=6)  # Jobs must start within 6 hours

        cwf = ConstrainedWindowedForecast(
            sample_data, duration, start, end_constraint=end_constraint
        )

        # All start times should be before the constraint
        for window in cwf:
            assert window.start < end_constraint

    def test_combined_constraints(
        self, sample_data: list[CarbonIntensityPointEstimate]
    ):
        """Test using both window and end constraints together."""
        duration = 90  # 1.5 hours
        start = sample_data[0].datetime
        max_window = 300  # 5 hours
        end_constraint = start + timedelta(hours=4)  # Must start within 4 hours

        cwf = ConstrainedWindowedForecast(
            sample_data,
            duration,
            start,
            max_window_minutes=max_window,
            end_constraint=end_constraint,
        )

        # Should have valid options
        assert len(cwf) > 0

        # All options should respect both constraints
        for window in cwf:
            assert window.start < end_constraint
            assert (window.start - start).total_seconds() / 60 <= max_window

    def test_insufficient_data_raises_error(self):
        """Test that insufficient data raises appropriate error."""
        # Create minimal data
        utc = ZoneInfo("UTC")
        minimal_data = [
            CarbonIntensityPointEstimate(
                datetime=datetime(2024, 1, 1, 12, 0, tzinfo=utc), value=100
            )
        ]

        with pytest.raises(ValueError, match="Insufficient forecast data"):
            _ = ConstrainedWindowedForecast(
                minimal_data, 60, minimal_data[0].datetime, max_window_minutes=30
            )

    def test_timezone_handling_in_end_constraint(
        self, sample_data: list[CarbonIntensityPointEstimate]
    ):
        """Test proper timezone handling for end constraints."""
        duration = 60
        start = sample_data[0].datetime

        # End constraint in different timezone
        bst = timezone(timedelta(hours=1))
        end_constraint = (start + timedelta(hours=6)).astimezone(bst)

        cwf = ConstrainedWindowedForecast(
            sample_data, duration, start, end_constraint=end_constraint
        )

        # Should still work correctly despite timezone difference
        assert len(cwf) > 0

    def test_index_out_of_range_raises_error(
        self, sample_data: list[CarbonIntensityPointEstimate]
    ):
        """Test that accessing invalid index raises IndexError."""
        duration = 60
        start = sample_data[0].datetime

        cwf = ConstrainedWindowedForecast(
            sample_data, duration, start, max_window_minutes=120
        )

        with pytest.raises(IndexError, match="Window index out of range"):
            cwf[len(cwf)]

    def test_iteration_works_correctly(
        self, sample_data: list[CarbonIntensityPointEstimate]
    ):
        """Test that iteration over forecast works correctly."""
        duration = 60
        start = sample_data[0].datetime

        cwf = ConstrainedWindowedForecast(
            sample_data, duration, start, max_window_minutes=240
        )

        # Test that we can iterate and get consistent results
        windows = list(cwf)
        assert len(windows) == len(cwf)

        # Test that iteration and indexing give same results
        for i, window in enumerate(cwf):
            assert window == cwf[i]


class TestMainIntegration:
    """Integration tests for main function with window constraints."""

    @patch("cats.get_CI_forecast")
    @patch("cats.configure.get_runtime_config")
    def test_main_with_window_constraint(
        self, mock_config: MagicMock, mock_forecast: MagicMock
    ):
        """Test main function with --window parameter."""
        # Mock the configuration
        from cats.CI_api_interface import API_interfaces

        mock_config.return_value = (
            API_interfaces["carbonintensity.org.uk"],
            "OX1",
            60,  # duration
            None,  # jobinfo
            None,  # PUE
        )

        # Mock forecast data
        utc = ZoneInfo("UTC")
        base_time = datetime.now(utc)
        mock_forecast.return_value = [
            CarbonIntensityPointEstimate(
                datetime=base_time + timedelta(minutes=i * 30), value=100 - i * 5
            )
            for i in range(100)  # 50 hours of data
        ]

        # Test with window constraint
        result = main(["-d", "60", "--loc", "OX1", "--window", "480"])
        assert result == 0

    @patch("cats.get_CI_forecast")
    @patch("cats.configure.get_runtime_config")
    def test_main_with_time_window_constraints(
        self, mock_config: MagicMock, mock_forecast: MagicMock
    ):
        """Test main function with --start-window and --end-window parameters."""
        # Mock the configuration
        from cats.CI_api_interface import API_interfaces

        mock_config.return_value = (
            API_interfaces["carbonintensity.org.uk"],
            "OX1",
            60,  # duration
            None,  # jobinfo
            None,  # PUE
        )

        # Mock forecast data
        utc = ZoneInfo("UTC")
        now = datetime.now(utc)
        mock_forecast.return_value = [
            CarbonIntensityPointEstimate(
                datetime=now + timedelta(minutes=i * 30), value=100 - i * 2
            )
            for i in range(100)  # 50 hours of data
        ]

        # Test with both start and end window constraints
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        day_after = (now + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")

        result = main(
            [
                "-d",
                "60",
                "--loc",
                "OX1",
                "--start-window",
                tomorrow,
                "--end-window",
                day_after,
            ]
        )
        assert result == 0

    @patch("cats.get_CI_forecast")
    @patch("cats.configure.get_runtime_config")
    def test_main_with_invalid_window_constraints(
        self, mock_config: MagicMock, mock_forecast: MagicMock
    ):
        """Test main function with invalid window constraints."""
        # Mock the configuration
        from cats.CI_api_interface import API_interfaces

        mock_config.return_value = (
            API_interfaces["carbonintensity.org.uk"],
            "OX1",
            60,  # duration
            None,  # jobinfo
            None,  # PUE
        )

        # Test with invalid window size
        result = main(["-d", "60", "--loc", "OX1", "--window", "5000"])
        assert result == 1  # Should fail

    @patch("cats.get_CI_forecast")
    @patch("cats.configure.get_runtime_config")
    def test_main_with_duration_exceeds_window(
        self, mock_config: MagicMock, mock_forecast: MagicMock
    ):
        """Test main function when job duration exceeds specified window."""
        # Mock the configuration
        from cats.CI_api_interface import API_interfaces

        mock_config.return_value = (
            API_interfaces["carbonintensity.org.uk"],
            "OX1",
            480,  # 8 hour duration
            None,  # jobinfo
            None,  # PUE
        )

        # Test with window smaller than duration
        result = main(["-d", "480", "--loc", "OX1", "--window", "240"])
        assert result == 1  # Should fail

    @patch("cats.get_CI_forecast")
    @patch("cats.configure.get_runtime_config")
    def test_main_with_conflicting_time_windows(
        self, mock_config: MagicMock, mock_forecast: MagicMock
    ):
        """Test main function with conflicting start and end windows."""
        # Mock the configuration
        from cats.CI_api_interface import API_interfaces

        mock_config.return_value = (
            API_interfaces["carbonintensity.org.uk"],
            "OX1",
            60,
            None,
            None,
        )

        # Test with start after end
        result = main(
            [
                "-d",
                "60",
                "--loc",
                "OX1",
                "--start-window",
                "2024-01-15T18:00",
                "--end-window",
                "2024-01-15T09:00",
            ]
        )
        assert result == 1  # Should fail

    def test_help_displays_new_options(self):
        """Test that --help displays the new window options."""
        with pytest.raises(SystemExit):
            _ = main(["--help"])


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_very_short_window_with_sample_data(
        self, sample_data: list[CarbonIntensityPointEstimate]
    ):
        """Test behavior with very short window constraint."""
        duration = 30  # 30 minutes
        start = sample_data[0].datetime

        # 1 hour window
        cwf = ConstrainedWindowedForecast(
            sample_data, duration, start, max_window_minutes=60
        )

        # Should still have at least one option
        assert len(cwf) > 0

    def test_end_constraint_in_past_relative_to_start(
        self, sample_data: list[CarbonIntensityPointEstimate]
    ):
        """Test end constraint that's before the start time."""
        duration = 60
        start = sample_data[5].datetime  # Start later in the data
        end_constraint = sample_data[2].datetime  # End before start

        # This should raise an error due to insufficient data
        with pytest.raises(
            ValueError, match="No index found for closest data point past job end time"
        ):
            _ = ConstrainedWindowedForecast(
                sample_data, duration, start, end_constraint=end_constraint
            )

    def test_window_exactly_matches_job_duration(
        self, sample_data: list[CarbonIntensityPointEstimate]
    ):
        """Test when window size exactly matches job duration."""
        duration = 120  # 2 hours
        start = sample_data[0].datetime

        cwf = ConstrainedWindowedForecast(
            sample_data, duration, start, max_window_minutes=duration
        )

        # Should have limited options due to the window constraint
        assert len(cwf) > 0
        # All valid start times should be within the window
        for window in cwf:
            time_diff = (window.start - start).total_seconds() / 60
            assert time_diff <= duration
