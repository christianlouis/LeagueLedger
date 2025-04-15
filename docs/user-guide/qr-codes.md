# QR Codes System

The QR code system is a core feature of LeagueLedger, enabling easy point attribution and event participation tracking. This guide explains how QR codes work in the system and how to use them effectively.

## Overview

LeagueLedger's QR code system allows organizers to:

- Create point-valued QR codes that users can scan
- Group codes into sets for specific events or purposes
- Track redemption and usage statistics
- Print codes for physical distribution

Users can scan these codes to:

- Earn points for themselves or their team
- Check in to events
- Claim achievements
- Verify attendance

## QR Code Types

LeagueLedger supports several types of QR codes:

### Point Value Codes

These codes represent specific point values that are awarded when scanned:

- **Standard Points**: Fixed point values (e.g., 5, 10, 25 points)
- **Variable Points**: Point values that may fluctuate based on factors like time, location, or number of scans
- **Team-Specific Points**: Codes that only award points to specific teams

### Functional Codes

These codes trigger specific actions in the system:

- **Check-In Codes**: For event attendance verification
- **Achievement Codes**: Unlock specific achievements when scanned
- **Registration Codes**: Link to team registration or event signup
- **Information Codes**: Open detailed information about an event or challenge

## Scanning QR Codes

### Mobile Scanning

To scan a QR code using a mobile device:

1. Log in to LeagueLedger on your mobile browser
2. Navigate to the "Scan" option in the menu
3. Allow camera permissions if prompted
4. Point your camera at the QR code
5. The system will automatically detect and process the code
6. A confirmation screen will display the points awarded or action taken

### Desktop Scanning

For desktop users with webcams:

1. Log in to LeagueLedger
2. Click on the "Scan QR Code" option in the navigation menu
3. Allow camera permissions when prompted
4. Position the QR code in front of your webcam
5. The system will process the code once detected

### Upload Scanning

If you have a QR code image file:

1. Go to the "Scan QR" page
2. Select the "Upload QR Code Image" option
3. Choose the image file from your device
4. Submit the image for processing

## Creating QR Codes (Administrators)

Administrators can create QR codes through the admin panel:

### Creating Individual QR Codes

1. Navigate to the Admin Panel > QR Codes
2. Click on "Create New QR Code"
3. Fill in the required information:
   - Point value
   - Description
   - Redemption limit (how many times it can be scanned)
   - Expiration date (if applicable)
   - Team restrictions (if applicable)
4. Click "Generate Code"
5. The new QR code will be displayed and added to the database

### Creating QR Code Sets

For organizing multiple codes together:

1. Go to Admin Panel > QR Codes > QR Sets
2. Select "Create New Set"
3. Provide a name and description for the set
4. Choose the number of codes to generate in this set
5. Configure the point values (fixed, random, or custom distribution)
6. Set any common properties (expiration, redemption limits)
7. Generate the set

### Printing QR Codes

To print physical copies of QR codes:

1. Go to Admin Panel > QR Codes or QR Sets
2. Select the code(s) you wish to print
3. Click "Print QR Codes"
4. Choose the print format:
   - Standard layout
   - Compact grid
   - Labels
   - Individual cards
5. Configure printing options (size, labels, etc.)
6. Click "Generate Printable PDF"
7. Print the generated document

## Managing QR Codes

### Monitoring Usage

Track QR code usage through the Admin Panel:

1. Go to Admin Panel > QR Codes
2. View the list of codes with usage statistics
3. Click on a specific code for detailed redemption history
4. See who scanned the code, when, and how many points were awarded

### Deactivating Codes

To disable a QR code:

1. Navigate to Admin Panel > QR Codes
2. Find the code you wish to deactivate
3. Click "Edit" or select the code
4. Toggle the "Active" status to inactive
5. Save changes

The code will remain in the system for record-keeping but can no longer be redeemed.

### Modifying Codes

To change a QR code's properties:

1. Go to Admin Panel > QR Codes
2. Select the code to modify
3. Click "Edit"
4. Update the desired properties
5. Save changes

!!! warning "Active Codes"
    Modifying the point value or redemption rules of already-distributed codes may cause confusion for users. Consider creating new codes instead of changing existing ones.

## Best Practices

### Security

- **Regenerate Codes Regularly**: Create new QR codes for each event to prevent reuse
- **Limit Redemptions**: Set appropriate scan limits to prevent abuse
- **Verify Location**: For important events, consider enabling location verification
- **Monitor Unusual Activity**: Check for patterns that might indicate QR code sharing

### Organization

- **Meaningful Names**: Use descriptive names for QR sets and codes
- **Color Coding**: Consider printing different point values on different colored paper
- **Tracking Identifiers**: Include visible IDs on printed codes for easy reference
- **Backup Copies**: Maintain digital backups of all generated codes

### Distribution

- **Strategic Placement**: Place higher-value codes in less obvious locations
- **Staffed Stations**: For high-value codes, consider having staff present
- **Time-Limited Availability**: Make codes available only during specific periods
- **Progressive Difficulty**: Structure code placement so finding codes gets progressively harder

## Troubleshooting

### Common Issues

#### QR Code Not Scanning

If a code isn't being recognized:

- Ensure adequate lighting
- Hold the device steady and at an appropriate distance
- Make sure the code isn't damaged or obscured
- Try using the image upload option instead

#### Points Not Awarded

If scanning succeeds but points aren't awarded:

- Check if the user is logged in
- Verify if the code has reached its redemption limit
- Check if the code has expired
- Confirm the user hasn't already scanned this code

#### Printing Problems

For issues with printed QR codes:

- Ensure printer resolution is adequate (300 DPI minimum recommended)
- Avoid scaling codes to very small sizes
- Print test codes and verify they scan correctly before mass production
- Use high-contrast printing (black on white background)

## Use Cases and Examples

### Hunt/Challenge Events

Create a scavenger hunt by placing QR codes throughout a venue:

- Place codes with varying point values in different locations
- Create clues that lead participants to code locations
- Track progress and award bonus points for completing the full hunt

### Attendance Tracking

Use QR codes for verifying attendance:

- Generate unique check-in codes for each event
- Place codes at event entrances
- Have participants scan on arrival
- Generate attendance reports from the admin panel

### Reward Programs

Implement a progressive reward system:

- Issue QR codes for completing certain tasks
- Create achievement sets that unlock when specific codes are collected
- Offer special rewards for collecting complete sets

## Next Steps

- [Team Management](teams.md): Learn how teams accumulate and manage points
- [Events](events.md): How to integrate QR codes with events
- [Points & Achievements](points-and-achievements.md): More about the points system
- [QR Code Management](../administration/qr-code-management.md): Advanced administration of QR codes