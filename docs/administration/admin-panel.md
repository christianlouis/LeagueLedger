# Admin Panel

The LeagueLedger Admin Panel provides administrators with powerful tools to manage all aspects of the system. This guide explains how to access and use the admin panel effectively.

## Accessing the Admin Panel

To access the admin panel:

1. Log in to LeagueLedger using an admin account
2. Click on your profile icon in the top-right corner
3. Select "Admin Panel" from the dropdown menu

!!! note "Admin Privileges"
    Only users with admin privileges can access the admin panel. If you don't see this option, contact your system administrator.

## Admin Panel Dashboard

The admin dashboard provides an overview of system activity and key metrics:

- **User Statistics**: Total users, active users, new registrations
- **Team Statistics**: Total teams, active teams, team distribution
- **Event Statistics**: Upcoming events, past events, attendance rates
- **System Health**: Database status, background tasks, recent errors

## Main Admin Sections

### User Management

In this section, you can manage all user accounts:

- **View Users**: See a list of all registered users with filtering options
- **Create Users**: Manually create new user accounts
- **Edit Users**: Modify existing user information
- **Verify/Unverify Users**: Manually verify or unverify user accounts
- **Reset Passwords**: Help users recover access to their accounts
- **Assign Roles**: Grant or revoke admin privileges
- **Disable Accounts**: Temporarily or permanently disable user accounts

### Team Management

Manage teams and their members:

- **View Teams**: Browse all teams with filtering and sorting options
- **Create Teams**: Create new teams manually
- **Edit Teams**: Update team information
- **Manage Members**: Add or remove team members
- **Transfer Ownership**: Change team ownership
- **Archive Teams**: Deactivate teams when needed

### QR Code Management

Create and manage QR codes for points and achievements:

- **Create QR Codes**: Generate new QR codes with specified point values
- **Create QR Sets**: Group QR codes into themed sets for events
- **View Usage**: Track which QR codes have been redeemed
- **Print QR Codes**: Generate printable sheets for distribution
- **Invalidate QR Codes**: Disable QR codes if needed

### Event Management

Create and manage events:

- **Create Events**: Set up new events with date, time, and location
- **Edit Events**: Modify event details
- **Assign QR Sets**: Connect QR code sets to specific events
- **Track Attendance**: Monitor event participation
- **View Results**: See points and achievements awarded at events

### System Configuration

Configure system-wide settings:

- **Email Settings**: Configure email server details and templates
- **OAuth Providers**: Set up social login integration
- **Appearance Settings**: Customize branding and UI elements
- **General Settings**: Adjust system behavior and defaults

## Administrative Tasks

### Running Reports

Generate reports to analyze system data:

1. Navigate to the "Reports" section in the admin panel
2. Select the report type (users, teams, events, etc.)
3. Set the parameters and date range
4. Click "Generate Report"
5. View on screen or export to CSV/PDF

### Managing Achievements

Create and assign achievements:

1. Go to the "Achievements" section
2. Create achievement types with names, descriptions, and icons
3. Set automatic achievement criteria or assign manually
4. Link achievements to QR codes if desired

### System Backup

Back up your system data:

1. Navigate to "System Tools"
2. Select "Backup Database"
3. Choose backup options (full or partial)
4. Initiate the backup process
5. Download the backup file or save to a configured location

## Best Practices

- **Regular Maintenance**: Schedule regular system checks and database optimization
- **User Audits**: Periodically review user accounts and permissions
- **QR Security**: Create new QR codes for each event to prevent reuse
- **Data Backup**: Back up the database before making significant changes
- **Testing**: Test new configurations in a staging environment before deploying

## Troubleshooting

### Common Issues

- **User Can't Log In**: Check account status, verification status, and credentials
- **QR Codes Not Working**: Verify QR code validity and ensure they're not already redeemed
- **Email Delivery Problems**: Check email server settings and test mail functionality
- **Performance Issues**: Monitor database size, optimize queries, check server resources

### Getting Support

If you encounter issues that you can't resolve:

1. Check the [documentation](../index.md) for relevant guidance
2. Consult the [developer documentation](../development/architecture.md) for technical details
3. Contact system support with specific error information and screenshots

## Next Steps

For more detailed information about specific administrative functions, please refer to the following guides:

- [User Management](user-management.md)
- [Team Management](team-management.md)
- [QR Code Management](qr-code-management.md)
- [Event Management](event-management.md)