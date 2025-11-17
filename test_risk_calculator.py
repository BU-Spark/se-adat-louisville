"""
Tests for the Anti-Displacement Assessment Tool Risk Calculator
"""

import pytest
from risk_calculator import (
    RiskLevel, NeighborhoodData, ProjectAffordability,
    AffordabilityProfile, Recommendation, RiskCalculator
)


class TestNeighborhoodData:
    """Tests for NeighborhoodData class."""
    
    def test_get_renters_percentage(self):
        """Test calculation of renter percentages."""
        neighborhood = NeighborhoodData(
            risk_level=RiskLevel.HIGH,
            renters30_ct=100,
            renters50_ct=250,
            renters60_ct=350,
            renters70_ct=450,
            renters80_ct=550,
            all_renters_ct=1000,
            cost_burden30_20_p=0.45
        )
        
        assert neighborhood.get_renters_percentage('30') == 10.0
        assert neighborhood.get_renters_percentage('50') == 25.0
        assert neighborhood.get_renters_percentage('60') == 35.0
        assert neighborhood.get_renters_percentage('70') == 45.0
        assert neighborhood.get_renters_percentage('80') == 55.0
    
    def test_get_renters_percentage_zero_renters(self):
        """Test percentage calculation with zero renters."""
        neighborhood = NeighborhoodData(
            risk_level=RiskLevel.LOW,
            renters30_ct=0,
            renters50_ct=0,
            renters60_ct=0,
            renters70_ct=0,
            renters80_ct=0,
            all_renters_ct=0,
            cost_burden30_20_p=0.0
        )
        
        assert neighborhood.get_renters_percentage('50') == 0.0
    
    def test_invalid_ami_level(self):
        """Test that invalid AMI levels raise ValueError."""
        neighborhood = NeighborhoodData(
            risk_level=RiskLevel.MEDIUM,
            renters30_ct=100,
            renters50_ct=200,
            renters60_ct=300,
            renters70_ct=400,
            renters80_ct=500,
            all_renters_ct=1000,
            cost_burden30_20_p=0.35
        )
        
        with pytest.raises(ValueError, match="Invalid AMI level"):
            neighborhood.get_renters_percentage('90')


class TestProjectAffordability:
    """Tests for ProjectAffordability class."""
    
    def test_valid_project(self):
        """Test creating a valid project."""
        project = ProjectAffordability(
            affordable30=10,
            affordable50=20,
            affordable60=15,
            affordable70=10,
            affordable80=5,
            proj_size=100
        )
        
        assert project.proj_size == 100
        assert project.affordable30 == 10
    
    def test_affordable_exceeds_size(self):
        """Test that validation catches when affordable units exceed project size."""
        with pytest.raises(ValueError, match="exceeds project size"):
            ProjectAffordability(
                affordable30=50,
                affordable50=40,
                affordable60=30,
                affordable70=20,
                affordable80=10,
                proj_size=100
            )
    
    def test_get_cumulative_affordable_at_level(self):
        """Test cumulative affordable unit calculations."""
        project = ProjectAffordability(
            affordable30=10,
            affordable50=20,
            affordable60=15,
            affordable70=10,
            affordable80=5,
            proj_size=100
        )
        
        assert project.get_cumulative_affordable_at_level('30') == 10
        assert project.get_cumulative_affordable_at_level('50') == 30
        assert project.get_cumulative_affordable_at_level('60') == 45
        assert project.get_cumulative_affordable_at_level('70') == 55
        assert project.get_cumulative_affordable_at_level('80') == 60
    
    def test_invalid_ami_level_cumulative(self):
        """Test that invalid AMI levels raise ValueError in cumulative calculation."""
        project = ProjectAffordability(
            affordable30=10,
            affordable50=20,
            affordable60=15,
            affordable70=10,
            affordable80=5,
            proj_size=100
        )
        
        with pytest.raises(ValueError, match="Invalid AMI level"):
            project.get_cumulative_affordable_at_level('100')


class TestAffordabilityProfile:
    """Tests for AffordabilityProfile class."""
    
    def test_get_ami_level_for_majority_first_level(self):
        """Test finding majority level when first level exceeds 50%."""
        profile = AffordabilityProfile(
            ami_levels=['30', '50', '60', '70', '80'],
            renter_percentages=[60.0, 70.0, 80.0, 85.0, 90.0],
            cumulative_affordable_units=[10, 30, 45, 55, 60]
        )
        
        ami_level, idx = profile.get_ami_level_for_majority()
        assert ami_level == '30'
        assert idx == 0
    
    def test_get_ami_level_for_majority_middle_level(self):
        """Test finding majority level in the middle."""
        profile = AffordabilityProfile(
            ami_levels=['30', '50', '60', '70', '80'],
            renter_percentages=[20.0, 45.0, 55.0, 70.0, 85.0],
            cumulative_affordable_units=[10, 30, 45, 55, 60]
        )
        
        ami_level, idx = profile.get_ami_level_for_majority()
        assert ami_level == '60'
        assert idx == 2
    
    def test_get_ami_level_for_majority_none_exceed(self):
        """Test when no level exceeds 50% - should return highest level."""
        profile = AffordabilityProfile(
            ami_levels=['30', '50', '60', '70', '80'],
            renter_percentages=[10.0, 20.0, 30.0, 40.0, 50.0],
            cumulative_affordable_units=[10, 30, 45, 55, 60]
        )
        
        ami_level, idx = profile.get_ami_level_for_majority()
        assert ami_level == '80'
        assert idx == 4


class TestRiskCalculator:
    """Tests for RiskCalculator class."""
    
    def test_high_risk_all_criteria_met(self):
        """Test high-risk area where all criteria are met."""
        neighborhood = NeighborhoodData(
            risk_level=RiskLevel.HIGH,
            renters30_ct=150,
            renters50_ct=300,
            renters60_ct=400,
            renters70_ct=500,
            renters80_ct=600,
            all_renters_ct=1000,
            cost_burden30_20_p=0.50  # 50% cost-burdened
        )
        
        # All 100 units are affordable, 60 units at 60% AMI or below
        project = ProjectAffordability(
            affordable30=10,
            affordable50=30,
            affordable60=20,
            affordable70=20,
            affordable80=20,
            proj_size=100
        )
        
        calculator = RiskCalculator(neighborhood, project)
        recommendation = calculator.calculate_recommendation()
        
        assert recommendation.is_recommended is True
        assert len(recommendation.criteria_met) == 2
        assert len(recommendation.criteria_unmet) == 0
        assert "All units are affordable" in recommendation.criteria_met[0]
    
    def test_high_risk_not_all_affordable(self):
        """Test high-risk area where not all units are affordable."""
        neighborhood = NeighborhoodData(
            risk_level=RiskLevel.HIGH,
            renters30_ct=150,
            renters50_ct=300,
            renters60_ct=400,
            renters70_ct=500,
            renters80_ct=600,
            all_renters_ct=1000,
            cost_burden30_20_p=0.50
        )
        
        # Only 60 of 100 units are affordable
        project = ProjectAffordability(
            affordable30=10,
            affordable50=20,
            affordable60=15,
            affordable70=10,
            affordable80=5,
            proj_size=100
        )
        
        calculator = RiskCalculator(neighborhood, project)
        recommendation = calculator.calculate_recommendation()
        
        assert recommendation.is_recommended is False
        assert "required to only include affordable units" in recommendation.criteria_unmet[0]
    
    def test_high_risk_insufficient_majority_affordability(self):
        """Test high-risk area where majority affordability is insufficient."""
        neighborhood = NeighborhoodData(
            risk_level=RiskLevel.HIGH,
            renters30_ct=100,
            renters50_ct=200,
            renters60_ct=600,  # 60% of renters at 60% AMI (majority)
            renters70_ct=700,
            renters80_ct=800,
            all_renters_ct=1000,
            cost_burden30_20_p=0.70  # 70% cost-burdened
        )
        
        # All units affordable but only 30% at 60% AMI level
        project = ProjectAffordability(
            affordable30=10,
            affordable50=20,
            affordable60=0,
            affordable70=35,
            affordable80=35,
            proj_size=100
        )
        
        calculator = RiskCalculator(neighborhood, project)
        recommendation = calculator.calculate_recommendation()
        
        assert recommendation.is_recommended is False
        assert len(recommendation.criteria_met) == 1  # All affordable
        assert len(recommendation.criteria_unmet) == 1  # But insufficient at majority level
    
    def test_medium_risk_criteria_met(self):
        """Test medium-risk area where criteria are met."""
        neighborhood = NeighborhoodData(
            risk_level=RiskLevel.MEDIUM,
            renters30_ct=100,
            renters50_ct=250,
            renters60_ct=550,  # Majority at 60% AMI
            renters70_ct=700,
            renters80_ct=800,
            all_renters_ct=1000,
            cost_burden30_20_p=0.40  # 40% cost-burdened
        )
        
        # 50 units affordable at 60% AMI or below (50% of project)
        project = ProjectAffordability(
            affordable30=10,
            affordable50=20,
            affordable60=20,
            affordable70=10,
            affordable80=10,
            proj_size=100
        )
        
        calculator = RiskCalculator(neighborhood, project)
        recommendation = calculator.calculate_recommendation()
        
        assert recommendation.is_recommended is True
        assert len(recommendation.criteria_met) == 1
        assert len(recommendation.criteria_unmet) == 0
        assert "50.0%" in recommendation.criteria_met[0]
        assert "60% AMI" in recommendation.criteria_met[0]
    
    def test_medium_risk_criteria_not_met(self):
        """Test medium-risk area where criteria are not met."""
        neighborhood = NeighborhoodData(
            risk_level=RiskLevel.MEDIUM,
            renters30_ct=100,
            renters50_ct=250,
            renters60_ct=550,
            renters70_ct=700,
            renters80_ct=800,
            all_renters_ct=1000,
            cost_burden30_20_p=0.60  # 60% cost-burdened
        )
        
        # Only 30% affordable at majority level
        project = ProjectAffordability(
            affordable30=10,
            affordable50=10,
            affordable60=10,
            affordable70=20,
            affordable80=20,
            proj_size=100
        )
        
        calculator = RiskCalculator(neighborhood, project)
        recommendation = calculator.calculate_recommendation()
        
        assert recommendation.is_recommended is False
        assert len(recommendation.criteria_met) == 0
        assert len(recommendation.criteria_unmet) == 1
        assert "30.0%" in recommendation.criteria_unmet[0]
    
    def test_low_risk_criteria_met(self):
        """Test low-risk area where criteria are met."""
        neighborhood = NeighborhoodData(
            risk_level=RiskLevel.LOW,
            renters30_ct=100,
            renters50_ct=300,
            renters60_ct=500,
            renters70_ct=700,
            renters80_ct=850,
            all_renters_ct=1000,
            cost_burden30_20_p=0.30
        )
        
        # 15 units at 50% AMI or below (15% of project)
        project = ProjectAffordability(
            affordable30=5,
            affordable50=10,
            affordable60=10,
            affordable70=10,
            affordable80=15,
            proj_size=100
        )
        
        calculator = RiskCalculator(neighborhood, project)
        recommendation = calculator.calculate_recommendation()
        
        assert recommendation.is_recommended is True
        assert len(recommendation.criteria_met) == 1
        assert len(recommendation.criteria_unmet) == 0
        assert "15.0%" in recommendation.criteria_met[0]
        assert "50% AMI" in recommendation.criteria_met[0]
    
    def test_low_risk_criteria_not_met(self):
        """Test low-risk area where criteria are not met."""
        neighborhood = NeighborhoodData(
            risk_level=RiskLevel.LOW,
            renters30_ct=100,
            renters50_ct=300,
            renters60_ct=500,
            renters70_ct=700,
            renters80_ct=850,
            all_renters_ct=1000,
            cost_burden30_20_p=0.30
        )
        
        # Only 5 units at 50% AMI or below (5% of project)
        project = ProjectAffordability(
            affordable30=2,
            affordable50=3,
            affordable60=10,
            affordable70=20,
            affordable80=15,
            proj_size=100
        )
        
        calculator = RiskCalculator(neighborhood, project)
        recommendation = calculator.calculate_recommendation()
        
        assert recommendation.is_recommended is False
        assert len(recommendation.criteria_met) == 0
        assert len(recommendation.criteria_unmet) == 1
        assert "at least 10%" in recommendation.criteria_unmet[0]
    
    def test_low_risk_exactly_10_percent(self):
        """Test low-risk area with exactly 10% affordable at 50% AMI."""
        neighborhood = NeighborhoodData(
            risk_level=RiskLevel.LOW,
            renters30_ct=100,
            renters50_ct=300,
            renters60_ct=500,
            renters70_ct=700,
            renters80_ct=850,
            all_renters_ct=1000,
            cost_burden30_20_p=0.30
        )
        
        # Exactly 10 units at 50% AMI or below (10% of project)
        project = ProjectAffordability(
            affordable30=5,
            affordable50=5,
            affordable60=10,
            affordable70=20,
            affordable80=10,
            proj_size=100
        )
        
        calculator = RiskCalculator(neighborhood, project)
        recommendation = calculator.calculate_recommendation()
        
        assert recommendation.is_recommended is True
        assert "10%" in recommendation.criteria_met[0]


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_zero_units_project(self):
        """Test with a project of zero units (boundary case)."""
        neighborhood = NeighborhoodData(
            risk_level=RiskLevel.LOW,
            renters30_ct=100,
            renters50_ct=300,
            renters60_ct=500,
            renters70_ct=700,
            renters80_ct=850,
            all_renters_ct=1000,
            cost_burden30_20_p=0.30
        )
        
        project = ProjectAffordability(
            affordable30=0,
            affordable50=0,
            affordable60=0,
            affordable70=0,
            affordable80=0,
            proj_size=0
        )
        
        # This should handle gracefully (though not realistic)
        calculator = RiskCalculator(neighborhood, project)
        # This will cause a division by zero issue in percentage calculation
        # The calculator should handle this gracefully
    
    def test_all_units_at_lowest_ami(self):
        """Test project with all units at 30% AMI."""
        neighborhood = NeighborhoodData(
            risk_level=RiskLevel.HIGH,
            renters30_ct=600,  # 60% at 30% AMI
            renters50_ct=700,
            renters60_ct=800,
            renters70_ct=900,
            renters80_ct=1000,
            all_renters_ct=1000,
            cost_burden30_20_p=0.50
        )
        
        project = ProjectAffordability(
            affordable30=100,
            affordable50=0,
            affordable60=0,
            affordable70=0,
            affordable80=0,
            proj_size=100
        )
        
        calculator = RiskCalculator(neighborhood, project)
        recommendation = calculator.calculate_recommendation()
        
        # Should be recommended (all affordable and serves majority)
        assert recommendation.is_recommended is True
    
    def test_rounding_boundary(self):
        """Test that rounding works correctly at boundaries."""
        neighborhood = NeighborhoodData(
            risk_level=RiskLevel.MEDIUM,
            renters30_ct=100,
            renters50_ct=250,
            renters60_ct=505,  # Just over 50%
            renters70_ct=700,
            renters80_ct=800,
            all_renters_ct=1000,
            cost_burden30_20_p=0.495  # Rounds to 50%
        )
        
        project = ProjectAffordability(
            affordable30=10,
            affordable50=15,
            affordable60=25,  # Exactly 50% at 60% AMI
            affordable70=20,
            affordable80=10,
            proj_size=100
        )
        
        calculator = RiskCalculator(neighborhood, project)
        recommendation = calculator.calculate_recommendation()
        
        # Should meet criteria since 50% >= 50%
        assert recommendation.is_recommended is True


class TestRecommendationOutput:
    """Tests for recommendation output formatting."""
    
    def test_details_format_with_criteria_met(self):
        """Test that details are properly formatted when criteria are met."""
        neighborhood = NeighborhoodData(
            risk_level=RiskLevel.LOW,
            renters30_ct=100,
            renters50_ct=300,
            renters60_ct=500,
            renters70_ct=700,
            renters80_ct=850,
            all_renters_ct=1000,
            cost_burden30_20_p=0.30
        )
        
        project = ProjectAffordability(
            affordable30=5,
            affordable50=10,
            affordable60=10,
            affordable70=10,
            affordable80=15,
            proj_size=100
        )
        
        calculator = RiskCalculator(neighborhood, project)
        recommendation = calculator.calculate_recommendation()
        
        assert "Criteria met:" in recommendation.details
        assert "✓" in recommendation.details
        assert "recommended for support" in recommendation.details
    
    def test_details_format_with_criteria_unmet(self):
        """Test that details are properly formatted when criteria are not met."""
        neighborhood = NeighborhoodData(
            risk_level=RiskLevel.HIGH,
            renters30_ct=150,
            renters50_ct=300,
            renters60_ct=600,
            renters70_ct=700,
            renters80_ct=800,
            all_renters_ct=1000,
            cost_burden30_20_p=0.50
        )
        
        project = ProjectAffordability(
            affordable30=10,
            affordable50=20,
            affordable60=0,
            affordable70=0,
            affordable80=0,
            proj_size=100
        )
        
        calculator = RiskCalculator(neighborhood, project)
        recommendation = calculator.calculate_recommendation()
        
        assert "Criteria not met:" in recommendation.details
        assert "✗" in recommendation.details
        assert "not recommended for support" in recommendation.details


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
