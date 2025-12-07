# Task Accuracy Improvement Plan

## Current State

| Rank | Task                    | Expert          | Accuracy | Test Results | Train Samples |
|------|-------------------------|-----------------|----------|--------------|---------------|
| 1    | click-billing-provider  | Provider Select | 0.0%     | 0/34         | 80            |
| 2    | click-treating-provider | Provider Select | 0.0%     | 0/33         | 80            |
| 3    | click-taskbar-icon      | Desktop         | 30.3%    | 10/33        | 80            |
| 4    | select-user             | Login Window    | 54.3%    | 50/92        | 80            |

---

## Root Cause Analysis

### Provider-Select Tasks (0% Accuracy) - CRITICAL BUGS

**Issue 1: Coordinate Mismatch Between Training and Tests**
- Location: `claim-window-generator/generator.py` lines 145, 266
- Training uses one coordinate calculation path, tests use another
- Expected normalized coordinates don't match `real_coords` pixel values
- Consistent offset: 12-18px X, 7-9px Y difference

**Issue 2: Dropdown Y-Offset Inconsistency**
- `tasks/click_dropdown.py` line 400: Applies -19px offset to dropdown
- `generator.py` line 145: NO offset applied
- Training and test data use incompatible dropdown positions

**Issue 3: Tolerance Field Ignored by Validator**
- Test cases specify per-task tolerance: `[74, 8]`
- Validator uses fixed 50 RU tolerance (ignores test field)
- Location: `rl-eval-env/src/rl_eval_env/validator.py` line 53

**Issue 4: Insufficient Training Data**
- Only 80 training samples vs 44,000 for login-window's select-user task
- No image reuse pattern implemented

### Desktop Taskbar (30.3% Accuracy)

**Issue 1: Tolerance Mismatch**
- Training tolerance: 50% of icon size (`[width//2, height//2]` = [13, 14] px)
- Test tolerance: Fixed 10 pixels (37% of icon)
- Model passes training criteria but fails stricter test criteria

**Issue 2: Unit Mismatch**
- Tolerance stored in pixels: `[10, 10]`
- Coordinates in RU units: `[536, 550]`
- Inconsistent comparison during evaluation

**Issue 3: Limited Test Diversity**
- Training: 3 different icons (od, explorer, edge)
- Testing: Only "Open Dental" icon (33 tests)

### Login Window (54.3% Accuracy) - Why It Works Best

1. **1:N Image Reuse**: 22 samples per image (22× data multiplier)
2. **Massive Training Data**: 44,000 samples from 2,000 images
3. **Deterministic Coordinates**: Computed from renderer bounds
4. **Clear Prompts**: "Select [name] from the list"
5. **Asymmetric Tolerance**: Strict X (user distinction), loose Y (row variation)

---

## Implementation Plan

### Phase 1: Fix Critical Bugs (Provider-Select)

#### 1.1 Unify Coordinate Generation
- **File**: `claim-window-generator/generator.py`
- **Change**: Use same coordinate calculation for training and tests
- **Details**:
  - Apply consistent -19px dropdown offset (or remove from both)
  - Ensure `expected_action.coordinate` = `normalize(real_coords)`
  - Add validation that coordinates round-trip correctly

#### 1.2 Fix Tolerance Handling
- **Option A**: Validator uses per-test tolerance field
  - File: `rl-eval-env/src/rl_eval_env/validator.py`
  - Change: Read tolerance from test case, not fixed constant
- **Option B**: Increase fixed tolerance
  - Set DEFAULT_COORD_TOLERANCE = 75 RU (matches test case needs)

#### 1.3 Add Coordinate Validation
- **File**: `claim-window-generator/generator.py`
- **Change**: After generating test cases, verify:
  ```python
  assert normalize(real_coords, image_size) == expected_action.coordinate
  ```

### Phase 2: Implement 1:N Image Reuse (All Generators)

#### 2.1 Provider-Select (claim-window-generator)
- **Current**: 80 samples from 80 images (1:1)
- **Target**: 2000+ samples from 100 images
- **Implementation**:
  - Generate one claim window with dropdown open
  - Create one sample per dropdown item (10-20 items)
  - Reuse same image for all provider selections

#### 2.2 Desktop (desktop-generator)
- **Current**: 80 samples from 80 images (1:1)
- **Target**: Multiple samples per taskbar configuration
- **Implementation**:
  - Generate one desktop with 3 taskbar icons
  - Create 3 samples (one per icon) from same image
  - 3× data multiplier

### Phase 3: Increase Training Data

#### 3.1 Update Dataset Configs
- **Provider-Select**: 200 base images × 10 providers = 2000 samples
- **Desktop Taskbar**: 300 base images × 3 icons = 900 samples
- **Login Window**: Already optimal (2000 × 22 = 44,000)

#### 3.2 Add Prompt Variations
- Include provider names in prompts: "Click on Dr. Smith in the billing provider dropdown"
- Add icon labels: "Double-click on Open Dental in the taskbar"

### Phase 4: Fix Tolerance Handling

#### 4.1 Normalize Tolerance Units
- **All generators**: Store tolerance in RU units, not pixels
- **Formula**: `tolerance_ru = tolerance_px * 1000 / max(width, height)`

#### 4.2 Match Training and Test Tolerance
- Use same tolerance calculation for both
- Training: `[width//2, height//2]` in pixels → convert to RU
- Testing: Use same converted RU values

### Phase 5: Improve Test Diversity

#### 5.1 Desktop Tests
- Test all 3 taskbar icons, not just "Open Dental"
- Vary icon positions across test images

#### 5.2 Provider-Select Tests
- Test both billing_provider and treating_provider
- Vary number of providers in dropdown

---

## Priority Order

1. **P0 - Critical**: Fix coordinate mismatch in provider-select (0% → ?%)
2. **P1 - High**: Implement 1:N reuse for provider-select
3. **P2 - Medium**: Fix tolerance unit mismatch in desktop
4. **P3 - Medium**: Increase training data volumes
5. **P4 - Low**: Improve test set diversity

---

## Expected Outcomes

| Task                    | Current | After P0 | After P1-P2 | Target |
|-------------------------|---------|----------|-------------|--------|
| click-billing-provider  | 0%      | 30-40%   | 60-70%      | 80%+   |
| click-treating-provider | 0%      | 30-40%   | 60-70%      | 80%+   |
| click-taskbar-icon      | 30%     | 30%      | 50-60%      | 75%+   |
| select-user             | 54%     | 54%      | 60-70%      | 80%+   |

---

## Files to Modify

### Provider-Select Fix
- `claim-window-generator/generator.py` (coordinate unification)
- `claim-window-generator/tasks/click_dropdown.py` (dropdown offset)
- `rl-eval-env/src/rl_eval_env/validator.py` (tolerance handling)

### 1:N Image Reuse
- `claim-window-generator/tasks/select_provider.py` (new task structure)
- `desktop-generator/tasks/click_taskbar_icon.py` (multi-sample generation)

### Config Updates
- `claim-window-generator/config/dataset.yaml` (increase base images)
- `desktop-generator/config/dataset.yaml` (increase base images)
