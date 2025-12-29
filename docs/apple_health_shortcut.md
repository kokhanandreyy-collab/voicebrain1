# How to Create the "VoiceBrainHealth" iOS Shortcut

To enable syncing nutrition and workout data from VoiceBrain to Apple Health, you need to create a simple iOS Shortcut. This shortcut acts as the bridge between the VoiceBrain web app and your device's Health Store.

## Prerequisites
- An iPhone with the **Shortcuts** app installed.
- **VoiceBrain** open in your browser (Safari/Chrome).

## Step-by-Step Guide

### 1. Create the Shortcut
1. Open the **Shortcuts** app.
2. Tap the **+** icon to create a new shortcut.
3. Tap the top name (New Shortcut) -> **Rename**.
4. Name it exactly: `VoiceBrainHealth` (Case sensitive).

### 2. Configure Input
1. In the search bar at the bottom, search for "**Receive What's on Screen**" (or just check the settings icon 'i' at the bottom).
2. Ensure **Show in Share Sheet** is enabled.
3. Tap on "Receive **Any** input from **Share Sheet**".
    - Change **Any** to **Text** and **URLs**.
    - If there's an option for "Input from...", select **Clipboard** as well if available, but primarily we need it to accept text input passed from the URL scheme.

### 3. Parse the Data
1. Search for "**Get Dictionary from Input**".
2. Add this action. Set the input to **Shortcut Input**.
    - If Shortcut Input isn't available directly, search for "**Get Text from Input**" first, then "**Get Dictionary from Text**".
    - *Goal*: You want the JSON string passed from VoiceBrain to be understood as a Dictionary.

### 4. Setup Variable (Optional but Clean)
1. Add "**Set Variable**".
2. Name: `HealthData`.
3. Value: The Dictionary from the previous step.

### 5. Log Nutrition Data
Add an "**If**" block to check for nutrition data.
1. Search **If**.
2. Condition: `HealthData` (Dictionary) -> Key: `nutrition` -> **has any value**.
3. **Inside the "If" block**:
    - **Get Dictionary Value**: Key `nutrition` from `HealthData`. Result: `NutritionDict`.
    
    - **Get Dictionary Value**: Key `calories` from `NutritionDict`. Result: `Calories`.
    - **Log Health Sample**:
        - Type: **Dietary Energy**
        - Value: `Calories` (Select 'As Number')
        - Unit: kcal
    
    - **Get Dictionary Value**: Key `protein` from `NutritionDict`. Result: `Protein`.
    - **Log Health Sample**:
        - Type: **Protein**
        - Value: `Protein`
        - Unit: g

    - *(Repeat for Carbs and Fat if desired)*

### 6. Log Workout Data
Add another "**If**" block for workouts.
1. Condition: `HealthData` -> Key `workout` -> **has any value**.
2. **Inside**:
    - **Get Dictionary Value**: Key `workout` from `HealthData`. Result: `WorkoutDict`.
    - **Get Dictionary Value**: Key `type` from `WorkoutDict`.
    - **Get Dictionary Value**: Key `duration_minutes` from `WorkoutDict`.
    - **Log Workout**:
        - Type: (Select Variable -> Type) *Note: You might need a mapping dictionary if "Running" string doesn't match Apple's strict Enum. For MVP, you can hardcode "Running" or ask user to confirm.*
        - Duration: Use the extracted minutes.

### 7. Confirmation
1. Add "**Show Notification**".
2. Message: "✅ VoiceBrain data synced to Health!"

### 8. Finish
Tap **Done**.

## How to Use
1. Open a Note in VoiceBrain that contains health data (e.g., "Ate an apple").
2. Look for the **"Health Data Detected"** card.
3. Tap **"Save to Apple Health"**.
4. A popup will ask to open Shortcuts. Tap **Open**.
5. The data will be saved instantly!

---
*Note: The first time you run this, iOS will ask for permission to write to Health. Tap "Allow All".*
