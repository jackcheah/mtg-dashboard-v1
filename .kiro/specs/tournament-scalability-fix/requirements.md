# Requirements Document - Tournament Scalability and Swiss Pairing Fix

## Introduction

The MTG Tournament Dashboard currently has significant limitations that prevent it from meeting its core requirement of supporting "teams of any number" and ensuring proper Swiss pairing without repeat matchups. After analyzing the codebase, documentation, and test files, several critical issues have been identified that need to be addressed.

## Current System Analysis

### What Works Well ✅
- Docker containerization and deployment
- Web-based dashboard interface
- Excel file loading and participant management
- Individual player scoring system
- Real-time timer functionality
- Modern UI/UX design

### Critical Issues Identified ❌

1. **Hard-coded Team Limits**: System is limited to exactly 8 teams (32 players) or 16 teams (64 players)
2. **Inflexible Tournament Structure**: Forces teams into groups instead of supporting single-tournament format
3. **Swiss Pairing Algorithm Failures**: Multiple algorithms implemented but still producing repeat matchups
4. **Constraint Satisfaction Issues**: Current algorithm fails for certain team configurations
5. **Scalability Problems**: Cannot handle variable team counts (4-20+ teams)

## Requirements

### Requirement 1: Variable Team Support

**User Story:** As a tournament organizer, I want to run tournaments with any number of teams from 4 to 20, so that I can accommodate different event sizes without system limitations.

#### Acceptance Criteria

1. WHEN the system loads participant data THEN it SHALL support between 4 and 20 teams
2. WHEN teams are loaded THEN the system SHALL NOT force them into predefined groups
3. WHEN tournament setup is initiated THEN it SHALL work with any valid team count
4. IF team count is not divisible by 4 THEN the system SHALL handle partial pods appropriately
5. WHEN displaying tournament structure THEN it SHALL show actual team count and pod distribution

### Requirement 2: Perfect Swiss Pairing

**User Story:** As a tournament organizer, I want to ensure no player faces the same opponent twice during Swiss rounds, so that the tournament maintains competitive integrity.

#### Acceptance Criteria

1. WHEN Swiss rounds are generated THEN no player SHALL face the same opponent more than once
2. WHEN a pod is created THEN it SHALL contain exactly one player from each of 4 different teams
3. WHEN pairing validation occurs THEN it SHALL report zero repeat matchup violations
4. IF perfect pairing is impossible THEN the system SHALL minimize repeat matchups and report statistics
5. WHEN tournament completes THEN validation SHALL confirm zero or minimal constraint violations

### Requirement 3: Robust Algorithm Implementation

**User Story:** As a developer, I want a reliable Swiss pairing algorithm that works consistently across all team configurations, so that tournaments never fail to generate.

#### Acceptance Criteria

1. WHEN tournament generation is attempted THEN it SHALL succeed for any valid team configuration
2. WHEN the algorithm encounters constraints THEN it SHALL use backtracking and constraint satisfaction
3. WHEN generation fails THEN it SHALL provide detailed error reporting
4. WHEN multiple attempts are needed THEN it SHALL try different approaches systematically
5. WHEN algorithm completes THEN it SHALL provide comprehensive statistics and validation

### Requirement 4: Flexible Tournament Formats

**User Story:** As a tournament organizer, I want to configure Swiss rounds (3 or 4) and handle different tournament sizes, so that I can adapt to various event formats.

#### Acceptance Criteria

1. WHEN setting up tournament THEN organizer SHALL be able to choose 3 or 4 Swiss rounds
2. WHEN team count varies THEN pod count SHALL be calculated as teams ÷ 4 (rounded appropriately)
3. WHEN pods are incomplete THEN system SHALL handle 3-player pods or bye rounds gracefully
4. WHEN tournament structure is displayed THEN it SHALL show accurate round and pod information
5. WHEN scoring occurs THEN it SHALL account for different pod sizes appropriately

### Requirement 5: Comprehensive Validation and Reporting

**User Story:** As a tournament organizer, I want detailed validation reports and statistics, so that I can verify tournament integrity and troubleshoot issues.

#### Acceptance Criteria

1. WHEN tournament is generated THEN system SHALL provide detailed constraint validation
2. WHEN violations occur THEN system SHALL report specific players and rounds involved
3. WHEN statistics are requested THEN system SHALL show pairing efficiency and coverage
4. WHEN validation completes THEN system SHALL indicate if tournament is "perfect" or has issues
5. WHEN debugging is needed THEN system SHALL provide player journey reports and opponent tracking

### Requirement 6: Backward Compatibility

**User Story:** As an existing user, I want the system to continue working with my current Excel files and tournament formats, so that I don't need to change my workflow.

#### Acceptance Criteria

1. WHEN existing Excel files are loaded THEN they SHALL continue to work without modification
2. WHEN 8-team tournaments are run THEN they SHALL work exactly as before
3. WHEN Docker deployment is used THEN it SHALL continue to work with new features
4. WHEN UI is accessed THEN existing functionality SHALL remain unchanged
5. WHEN scoring is performed THEN existing point system SHALL be maintained

### Requirement 7: Performance and Reliability

**User Story:** As a tournament organizer, I want tournament generation to complete quickly and reliably, so that I can start events without delays.

#### Acceptance Criteria

1. WHEN tournament generation starts THEN it SHALL complete within 30 seconds for up to 20 teams
2. WHEN algorithm runs THEN it SHALL provide progress feedback for long operations
3. WHEN generation fails THEN it SHALL retry with different approaches automatically
4. WHEN system is under load THEN it SHALL maintain responsive UI
5. WHEN multiple tournaments are generated THEN performance SHALL remain consistent

## Success Criteria

The requirements will be considered successfully implemented when:

1. ✅ System supports 4-20 teams without hard-coded limits
2. ✅ Swiss pairing produces zero repeat matchups for standard configurations
3. ✅ Tournament generation succeeds 100% of the time for valid inputs
4. ✅ Comprehensive validation reports are available
5. ✅ Existing functionality remains unchanged
6. ✅ Performance meets specified benchmarks
7. ✅ All test suites pass with new implementation

## Out of Scope

- Changes to scoring system (5 points win, 0 loss, 1 draw)
- Modifications to UI design or layout
- Changes to Excel file format requirements
- Alterations to Docker deployment process
- Modifications to timer functionality
- Changes to final round/playoff structure