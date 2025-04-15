# LeagueLedger <img src="app/static/images/logos/monogram.png" alt="LeagueLedger Logo" width="40" align="right">

A modern web application for managing sports league loyalty programs, events, and rewards through QR codes.

## Features

- **Team Management**: Create and manage teams with member profiles
- **QR Code Redemption**: Generate and scan QR codes for points and rewards
- **Leaderboards**: Track team and individual standings
- **OAuth Integration**: Multiple social login options including Google, GitHub, LinkedIn, Facebook, and netID
- **Internationalization**: Multi-language support with English and German locales
- **Responsive Design**: Mobile-friendly interface built with Tailwind CSS

## Quick Start

1. **Clone the repository**
   ```
   git clone https://github.com/yourusername/LeagueLedger.git
   cd LeagueLedger
   ```

2. **Set up environment variables**
   ```
   cp .env.template .env
   # Edit .env with your configuration
   ```

3. **Run with Docker**
   ```
   docker-compose up -d
   ```

4. **Or run locally**
   ```
   pip install -r requirements.txt
   python app/main.py
   ```

5. **Access the application**
   ```
   http://localhost:8000
   ```

## Documentation

Detailed documentation is available in the `/docs` directory. Generate the complete documentation site with:

```
mkdocs serve
```

## License

This project is licensed under the terms of the license file included in this repository.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.