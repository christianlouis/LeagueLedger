# Email Testing with Mailhog

This project is configured to use Mailhog for email testing during development. Mailhog provides a fake SMTP server that captures all outgoing emails and displays them in a web interface instead of actually sending them.

## How it Works

When running the application in the Docker development environment, all emails are sent to the Mailhog container instead of real recipients. This allows you to test email functionality without worrying about sending actual emails.

## Viewing Captured Emails

1. Start the Docker containers using:
   ```
   docker-compose up -d
   ```

2. Access the Mailhog web interface at:
   ```
   http://localhost:8025
   ```

3. Any emails sent by the application will appear in this interface, where you can:
   - View the email content (HTML and text versions)
   - See all recipients, headers, and attachments
   - Release emails to actually be delivered (if configured)
   - Delete emails

## Configuration

The Mailhog SMTP server is configured with:
- Host: `mailhog`
- Port: `1025`
- No authentication required

These settings are already configured in the `.env` file and the Docker environment variables.

## Switching to Production Email

When deploying to production, update the SMTP configuration in the `.env` file to use your actual email service provider. There are commented-out production settings in the `.env` file that you can uncomment and configure.

## Troubleshooting

If emails aren't appearing in the Mailhog interface:

1. Make sure all containers are running:
   ```
   docker-compose ps
   ```

2. Check the logs for errors:
   ```
   docker-compose logs app
   docker-compose logs mailhog
   ```

3. Verify that the application is using the correct SMTP settings by checking the environment variables passed to the app container.
