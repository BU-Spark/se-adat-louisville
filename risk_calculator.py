"""
Anti-Displacement Assessment Tool - Risk Calculator

This module calculates housing project recommendations based on displacement risk
and affordability criteria for Louisville Metro housing projects.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
from enum import Enum


class RiskLevel(Enum):
    """Enumeration of displacement risk levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class NeighborhoodData:
    """Data about a neighborhood for risk assessment.
    
    Attributes:
        risk_level: The displacement risk level (low, medium, high)
        renters30_ct: Number of renters earning below 30% AMI
        renters50_ct: Number of renters earning below 50% AMI
        renters60_ct: Number of renters earning below 60% AMI
        renters70_ct: Number of renters earning below 70% AMI
        renters80_ct: Number of renters earning below 80% AMI
        all_renters_ct: Total number of renters in the area
        cost_burden30_20_p: Proportion of households that are cost-burdened
    """
    risk_level: RiskLevel
    renters30_ct: float
    renters50_ct: float
    renters60_ct: float
    renters70_ct: float
    renters80_ct: float
    all_renters_ct: float
    cost_burden30_20_p: float
    
    def get_renters_percentage(self, ami_level: str) -> float:
        """Calculate the percentage of renters at or below a given AMI level.
        
        Args:
            ami_level: One of '30', '50', '60', '70', '80'
            
        Returns:
            Percentage (0-100) of renters at or below the AMI level
        """
        renter_counts = {
            '30': self.renters30_ct,
            '50': self.renters50_ct,
            '60': self.renters60_ct,
            '70': self.renters70_ct,
            '80': self.renters80_ct
        }
        
        if ami_level not in renter_counts:
            raise ValueError(f"Invalid AMI level: {ami_level}")
        
        if self.all_renters_ct == 0:
            return 0.0
            
        return round((renter_counts[ami_level] / self.all_renters_ct) * 100, 0)


@dataclass
class ProjectAffordability:
    """Affordable unit counts for a housing project.
    
    Attributes:
        affordable30: Number of units affordable at 30% AMI
        affordable50: Number of units affordable at 50% AMI
        affordable60: Number of units affordable at 60% AMI
        affordable70: Number of units affordable at 70% AMI
        affordable80: Number of units affordable at 80% AMI
        proj_size: Total number of units in the project
    """
    affordable30: int
    affordable50: int
    affordable60: int
    affordable70: int
    affordable80: int
    proj_size: int
    
    def __post_init__(self):
        """Validate that affordable units don't exceed project size."""
        total_affordable = (self.affordable30 + self.affordable50 + 
                          self.affordable60 + self.affordable70 + self.affordable80)
        if total_affordable > self.proj_size:
            raise ValueError(
                f"Total affordable units ({total_affordable}) exceeds "
                f"project size ({self.proj_size})"
            )
    
    def get_cumulative_affordable_at_level(self, ami_level: str) -> int:
        """Get cumulative affordable units at or below a given AMI level.
        
        Args:
            ami_level: One of '30', '50', '60', '70', '80'
            
        Returns:
            Cumulative count of units affordable at or below the AMI level
        """
        cumulative = {
            '30': self.affordable30,
            '50': self.affordable30 + self.affordable50,
            '60': self.affordable30 + self.affordable50 + self.affordable60,
            '70': self.affordable30 + self.affordable50 + self.affordable60 + self.affordable70,
            '80': self.affordable30 + self.affordable50 + self.affordable60 + 
                  self.affordable70 + self.affordable80
        }
        
        if ami_level not in cumulative:
            raise ValueError(f"Invalid AMI level: {ami_level}")
            
        return cumulative[ami_level]


@dataclass
class AffordabilityProfile:
    """Profile matching AMI levels to renter populations and project affordability."""
    ami_levels: List[str]
    renter_percentages: List[float]
    cumulative_affordable_units: List[int]
    
    def get_ami_level_for_majority(self) -> Tuple[str, int]:
        """Find the lowest AMI level where >50% of renters are served.
        
        Returns:
            Tuple of (AMI level string, index in the profile lists)
        """
        for idx, pct in enumerate(self.renter_percentages):
            if pct > 50:
                return self.ami_levels[idx], idx
        # If no level exceeds 50%, return the highest level
        return self.ami_levels[-1], len(self.ami_levels) - 1


@dataclass
class Recommendation:
    """Project recommendation result.
    
    Attributes:
        is_recommended: Whether the project is recommended for support
        criteria_met: List of criteria that were met
        criteria_unmet: List of criteria that were not met
        details: Detailed explanation of the recommendation
    """
    is_recommended: bool
    criteria_met: List[str]
    criteria_unmet: List[str]
    details: str


class RiskCalculator:
    """Calculator for housing project recommendations based on displacement risk."""
    
    AMI_LEVELS = ['30', '50', '60', '70', '80']
    AMI_LABELS = {
        '30': '30% AMI',
        '50': '50% AMI',
        '60': '60% AMI',
        '70': '70% AMI',
        '80': '80% AMI'
    }
    
    def __init__(self, neighborhood: NeighborhoodData, project: ProjectAffordability):
        """Initialize calculator with neighborhood and project data.
        
        Args:
            neighborhood: Neighborhood demographic and risk data
            project: Project affordability breakdown
        """
        self.neighborhood = neighborhood
        self.project = project
        self._build_affordability_profile()
    
    def _build_affordability_profile(self) -> None:
        """Build the affordability profile for analysis."""
        self.profile = AffordabilityProfile(
            ami_levels=self.AMI_LEVELS,
            renter_percentages=[
                self.neighborhood.get_renters_percentage(level) 
                for level in self.AMI_LEVELS
            ],
            cumulative_affordable_units=[
                self.project.get_cumulative_affordable_at_level(level)
                for level in self.AMI_LEVELS
            ]
        )
    
    def calculate_recommendation(self) -> Recommendation:
        """Calculate whether the project is recommended based on risk level.
        
        Returns:
            Recommendation object with criteria evaluation and details
        """
        if self.neighborhood.risk_level == RiskLevel.HIGH:
            return self._evaluate_high_risk()
        elif self.neighborhood.risk_level == RiskLevel.MEDIUM:
            return self._evaluate_medium_risk()
        else:  # LOW
            return self._evaluate_low_risk()
    
    def _evaluate_high_risk(self) -> Recommendation:
        """Evaluate project in high-risk area.
        
        High-risk criteria:
        1. All units must be affordable
        2. Share of units affordable to majority of renters >= cost burden percentage
        """
        criteria_met = []
        criteria_unmet = []
        
        # Criterion 1: All units must be affordable
        all_units_affordable = (
            self.project.get_cumulative_affordable_at_level('80') == 
            self.project.proj_size
        )
        
        if all_units_affordable:
            criteria_met.append("All units are affordable")
        else:
            criteria_unmet.append(
                "Projects in high-risk areas are required to only include affordable units"
            )
        
        # Criterion 2: Affordability for majority >= cost burden
        majority_ami, majority_idx = self.profile.get_ami_level_for_majority()
        majority_affordable_units = self.profile.cumulative_affordable_units[majority_idx]
        majority_affordable_pct = round(
            (majority_affordable_units / self.project.proj_size) * 100, 0
        )
        cost_burden_pct = round(self.neighborhood.cost_burden30_20_p * 100, 0)
        
        majority_meets_burden = majority_affordable_pct >= cost_burden_pct
        
        if majority_meets_burden:
            criteria_met.append(
                f"{majority_affordable_pct}% of units are affordable at "
                f"{self.AMI_LABELS[majority_ami]}, meeting the requirement that "
                f"this share be >= {cost_burden_pct}% (cost-burdened households)"
            )
        else:
            criteria_unmet.append(
                f"{majority_affordable_pct}% of units are affordable at "
                f"{self.AMI_LABELS[majority_ami]}. The share must be >= "
                f"{cost_burden_pct}% (cost-burdened households)"
            )
        
        is_recommended = all_units_affordable and majority_meets_burden
        
        details = self._format_details(criteria_met, criteria_unmet, is_recommended)
        
        return Recommendation(
            is_recommended=is_recommended,
            criteria_met=criteria_met,
            criteria_unmet=criteria_unmet,
            details=details
        )
    
    def _evaluate_medium_risk(self) -> Recommendation:
        """Evaluate project in medium-risk area.
        
        Medium-risk criterion:
        - Share of units affordable to majority of renters >= cost burden percentage
        """
        criteria_met = []
        criteria_unmet = []
        
        majority_ami, majority_idx = self.profile.get_ami_level_for_majority()
        majority_affordable_units = self.profile.cumulative_affordable_units[majority_idx]
        majority_affordable_pct = round(
            (majority_affordable_units / self.project.proj_size) * 100, 0
        )
        cost_burden_pct = round(self.neighborhood.cost_burden30_20_p * 100, 0)
        
        majority_meets_burden = majority_affordable_pct >= cost_burden_pct
        
        if majority_meets_burden:
            criteria_met.append(
                f"{majority_affordable_pct}% of units are affordable at "
                f"{self.AMI_LABELS[majority_ami]}, meeting the requirement that "
                f"this share be >= {cost_burden_pct}% (cost-burdened households)"
            )
        else:
            criteria_unmet.append(
                f"{majority_affordable_pct}% of units are affordable at "
                f"{self.AMI_LABELS[majority_ami]}. The share must be >= "
                f"{cost_burden_pct}% (cost-burdened households)"
            )
        
        is_recommended = majority_meets_burden
        
        details = self._format_details(criteria_met, criteria_unmet, is_recommended)
        
        return Recommendation(
            is_recommended=is_recommended,
            criteria_met=criteria_met,
            criteria_unmet=criteria_unmet,
            details=details
        )
    
    def _evaluate_low_risk(self) -> Recommendation:
        """Evaluate project in low-risk area.
        
        Low-risk criterion:
        - At least 10% of units must be affordable at 50% AMI or below
        """
        criteria_met = []
        criteria_unmet = []
        
        affordable_50_units = self.project.get_cumulative_affordable_at_level('50')
        affordable_50_pct = affordable_50_units / self.project.proj_size
        
        meets_10_percent = affordable_50_pct >= 0.1
        
        if meets_10_percent:
            criteria_met.append(
                f"{round(affordable_50_pct * 100, 0)}% of units are affordable at "
                f"50% AMI or below, meeting the 10% requirement"
            )
        else:
            criteria_unmet.append(
                "Projects in low-risk areas must include at least 10% of units "
                "affordable at 50% AMI or below"
            )
        
        is_recommended = meets_10_percent
        
        details = self._format_details(criteria_met, criteria_unmet, is_recommended)
        
        return Recommendation(
            is_recommended=is_recommended,
            criteria_met=criteria_met,
            criteria_unmet=criteria_unmet,
            details=details
        )
    
    def _format_details(self, criteria_met: List[str], 
                       criteria_unmet: List[str], is_recommended: bool) -> str:
        """Format the detailed recommendation text.
        
        Args:
            criteria_met: List of criteria that were met
            criteria_unmet: List of criteria that were not met
            is_recommended: Whether project is recommended
            
        Returns:
            Formatted details string
        """
        details = []
        
        if criteria_met:
            details.append("Criteria met:")
            for criterion in criteria_met:
                details.append(f"  ✓ {criterion}")
        
        if criteria_unmet:
            details.append("\nCriteria not met:")
            for criterion in criteria_unmet:
                details.append(f"  ✗ {criterion}")
        
        details.append("")
        if is_recommended:
            details.append("This project is recommended for support.")
        else:
            details.append(
                "This project is not recommended for support until it meets these conditions."
            )
        
        return "\n".join(details)
