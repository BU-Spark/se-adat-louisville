"""
Unit Tests for ADAT Data Preparation Module
"""

import pytest
import numpy as np
from data_prep_simple import (
    med_lin_est,
    renter_adj,
    calculate_risk_level,
    validate_project_data
)


class TestMedLinEst:
    """Test median linear interpolation function"""
    
    def test_basic_median(self):
        """Test basic median calculation"""
        names = ['rent_500', 'rent_1000', 'rent_1500']
        values = [10, 20, 10]
        result = med_lin_est(names, values)
        assert result is not None
        assert isinstance(result, (float, np.floating))
    
    def test_empty_values(self):
        """Test with all zero values"""
        names = ['rent_500', 'rent_1000']
        values = [0, 0]
        result = med_lin_est(names, values)
        assert np.isnan(result)
    
    def test_single_bin(self):
        """Test with values in single bin"""
        names = ['rent_500', 'rent_1000', 'rent_1500']
        values = [0, 100, 0]
        result = med_lin_est(names, values)
        assert result is not None


class TestRenterAdj:
    """Test renter FMI adjustment function"""
    
    def test_basic_adjustment(self):
        """Test basic FMI adjustment"""
        names = ['inc_30000', 'inc_50000', 'inc_70000']
        values = [100, 50, 25]
        fmi = 55000
        result = renter_adj(names, values, fmi)
        assert result > 0
        assert isinstance(result, (int, float))
    
    def test_fmi_exceeds_all_bins(self):
        """Test when FMI exceeds all income bins"""
        names = ['inc_30000', 'inc_50000']
        values = [100, 50]
        fmi = 100000
        result = renter_adj(names, values, fmi)
        assert result == 150  # Sum of all values


class TestCalculateRiskLevel:
    """Test displacement risk calculation"""
    
    def test_high_risk(self):
        """Test high risk scenario"""
        result = calculate_risk_level(
            median_income=40000,
            median_rent=1200,
            rent_change=0.25
        )
        assert result == 'high'
    
    def test_medium_risk(self):
        """Test medium risk scenario"""
        result = calculate_risk_level(
            median_income=45000,
            median_rent=1000,
            rent_change=0.15
        )
        assert result == 'medium'
    
    def test_low_risk(self):
        """Test low risk scenario"""
        result = calculate_risk_level(
            median_income=60000,
            median_rent=900,
            rent_change=0.05
        )
        assert result == 'low'


class TestValidateProjectData:
    """Test project data validation"""
    
    def test_valid_project(self):
        """Test valid project data"""
        project = {
            'location': 'Downtown Louisville',
            'units': 100,
            'affordable_units': 30
        }
        is_valid, error = validate_project_data(project)
        assert is_valid is True
        assert error == ""
    
    def test_missing_field(self):
        """Test missing required field"""
        project = {
            'location': 'Downtown Louisville',
            'units': 100
        }
        is_valid, error = validate_project_data(project)
        assert is_valid is False
        assert "Missing required field" in error
    
    def test_invalid_units(self):
        """Test invalid units value"""
        project = {
            'location': 'Downtown Louisville',
            'units': -5,
            'affordable_units': 10
        }
        is_valid, error = validate_project_data(project)
        assert is_valid is False
        assert "positive number" in error
    
    def test_affordable_exceeds_total(self):
        """Test affordable units exceeding total"""
        project = {
            'location': 'Downtown Louisville',
            'units': 50,
            'affordable_units': 75
        }
        is_valid, error = validate_project_data(project)
        assert is_valid is False
        assert "cannot exceed" in error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
