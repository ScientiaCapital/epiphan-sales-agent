"""Tests for approval pattern learner."""

from app.services.autonomous.learner import ApprovalLearner


class TestNormalizeTitle:
    def test_vp_normalization(self) -> None:
        learner = ApprovalLearner()
        assert learner._normalize_title("Vice President of IT") == "vp_it"

    def test_director_normalization(self) -> None:
        learner = ApprovalLearner()
        result = learner._normalize_title("Director of AV Services")
        assert result is not None
        assert "director" in result

    def test_none_input(self) -> None:
        learner = ApprovalLearner()
        assert learner._normalize_title(None) is None

    def test_truncation(self) -> None:
        learner = ApprovalLearner()
        long_title = "Vice President of Information Technology and Digital Transformation Services"
        result = learner._normalize_title(long_title)
        assert result is not None
        assert len(result) <= 50

    def test_removes_noise_words(self) -> None:
        learner = ApprovalLearner()
        result = learner._normalize_title("Head of IT & Operations")
        assert result is not None
        assert "&" not in result
